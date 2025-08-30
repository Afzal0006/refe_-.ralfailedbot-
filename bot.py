import os
import logging
from datetime import datetime
from functools import wraps

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)
from pymongo import MongoClient
from dotenv import load_dotenv

# ========= Load env =========
load_dotenv(".env")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")
REQUIRED_CHANNELS = [c.strip() for c in os.environ.get("REQUIRED_CHANNELS", "").split(",") if c.strip()]
REQUIRED_CHANNEL_URLS = [u.strip() for u in os.environ.get("REQUIRED_CHANNEL_URLS", "").split(",") if u.strip()]
START_IMAGE_URL = os.environ.get("START_IMAGE_URL", "")
WELCOME_IMAGE_URL = os.environ.get("WELCOME_IMAGE_URL", "")
WITHDRAW_MIN_POINTS = int(os.environ.get("WITHDRAW_MIN_POINTS", "10"))
ADMIN_IDS = {int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()}

if not BOT_TOKEN or not MONGO_URI or not REQUIRED_CHANNELS:
    raise RuntimeError("Please set BOT_TOKEN, MONGO_URI, REQUIRED_CHANNELS in .env")

# ========= Logging =========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger("ref-bot")

# ========= Mongo =========
client = MongoClient(MONGO_URI)
db = client["referral_bot"]
users = db["users"]                # {user_id, points, referred_by, referrals[], created_at}
withdrawals = db["withdrawals"]    # {user_id, points, contact, status, created_at}
redeem_codes = db["redeem_codes"]  # {code, points, redeemed_by[], multi_use(bool)}
states = db["states"]              # {user_id, state, meta}

# ========= Conversation States =========
REDEEM_AWAIT_CODE = 1
WITHDRAW_AWAIT_DETAILS = 2

# ========= Helpers =========
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id if update.effective_user else 0
        if uid not in ADMIN_IDS:
            await update.effective_message.reply_text("This command is restricted to admins.")
            return
        return await func(update, context)
    return wrapper

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Refer & Earn", callback_data="menu_ref")],
        [
            InlineKeyboardButton("📊 My Points", callback_data="menu_points"),
            InlineKeyboardButton("💸 Withdraw Points", callback_data="menu_withdraw"),
        ],
        [
            InlineKeyboardButton("🛟 Support", callback_data="menu_support"),
            InlineKeyboardButton("📖 How to Use", callback_data="menu_how"),
        ],
        [InlineKeyboardButton("🎟️ Redeem Code", callback_data="menu_redeem")]
    ])

def start_join_kb(bot_username: str):
    # Build visible join buttons
    rows = []
    for idx, ch in enumerate(REQUIRED_CHANNELS, start=1):
        if REQUIRED_CHANNEL_URLS and len(REQUIRED_CHANNEL_URLS) >= idx and REQUIRED_CHANNEL_URLS[idx-1]:
            url = REQUIRED_CHANNEL_URLS[idx-1]
        else:
            # default t.me link
            uname = ch if str(ch).startswith("@") else ch
            if str(uname).startswith("@"):
                url = f"https://t.me/{uname[1:]}"
            else:
                url = f"https://t.me/c/{uname}"  # numeric id fallback (not always works)
        rows.append([InlineKeyboardButton(f"Channel {idx}", url=url)])
    rows.append([InlineKeyboardButton("✅ Joined", callback_data="verify_join")])
    return InlineKeyboardMarkup(rows)

async def get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    if not getattr(context.application, "cached_bot_username", None):
        me = await context.bot.get_me()
        context.application.cached_bot_username = me.username
    return context.application.cached_bot_username

async def is_member_of_all(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    for ch in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ("left", "kicked"):
                return False
        except Exception as e:
            log.warning(f"get_chat_member failed for {ch}: {e}")
            # If we cannot check, treat as not joined.
            return False
    return True

def ensure_user(user_id: int):
    u = users.find_one({"user_id": user_id})
    if not u:
        users.insert_one({
            "user_id": user_id,
            "points": 0,
            "referred_by": None,
            "referrals": [],
            "created_at": datetime.utcnow()
        })

def add_point(user_id: int, pts: int = 1):
    users.update_one({"user_id": user_id}, {"$inc": {"points": pts}})

def set_referred_by(user_id: int, ref_id: int):
    users.update_one({"user_id": user_id}, {"$set": {"referred_by": ref_id}})

def add_referral(referrer_id: int, new_user_id: int):
    users.update_one({"user_id": referrer_id}, {"$addToSet": {"referrals": new_user_id}})

async def send_welcome_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    caption = "Welcome to **Manu** 🎉\nUse button to navigate 👇"
    if WELCOME_IMAGE_URL:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=WELCOME_IMAGE_URL,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb()
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb()
        )

# ========= Handlers =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    args = context.args

    ensure_user(user.id)

    # Handle referral deep-link: /start <ref_user_id>
    referred_by_id = None
    if args:
        try:
            referred_by_id = int(args[0])
        except:
            referred_by_id = None

    # If new user (no points and no referrals field?) set referral
    existing = users.find_one({"user_id": user.id})
    if existing and existing.get("referred_by") is None and referred_by_id and referred_by_id != user.id:
        # Only count if the referred_by exists & new user hasn't been credited before
        ref_exists = users.find_one({"user_id": referred_by_id})
        if ref_exists:
            set_referred_by(user.id, referred_by_id)
            add_referral(referred_by_id, user.id)
            add_point(referred_by_id, 1)

    bot_username = await get_bot_username(context)

    # Send join instruction (with image) + verify button
    text = "U need to join channel for free accounts.."
    if START_IMAGE_URL:
        msg = await context.bot.send_photo(
            chat_id=chat.id,
            photo=START_IMAGE_URL,
            caption=text,
            reply_markup=start_join_kb(bot_username),
        )
    else:
        msg = await context.bot.send_message(
            chat_id=chat.id,
            text=text,
            reply_markup=start_join_kb(bot_username),
        )

    # Store the message id so we can delete after verification
    states.update_one(
        {"user_id": user.id},
        {"$set": {"state": "await_join_verify", "meta": {"msg_id": msg.message_id}}},
        upsert=True
    )

async def cb_verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    chat_id = update.effective_chat.id

    if await is_member_of_all(context, user.id):
        # Delete the start message
        st = states.find_one({"user_id": user.id})
        if st and st.get("meta", {}).get("msg_id"):
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=st["meta"]["msg_id"])
            except Exception as e:
                log.info(f"Couldn't delete msg: {e}")

        # Clear state
        states.delete_one({"user_id": user.id})

        # Send main menu
        await send_welcome_menu(update, context)
    else:
        await query.edit_message_caption(
            caption="Please join **all** channels first, then tap **Joined ✅**.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=start_join_kb(await get_bot_username(context))
        )

async def cb_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = update.effective_user.id
    await query.answer()

    if data == "menu_ref":
        bot_username = await get_bot_username(context)
        ref_link = f"https://t.me/{bot_username}?start={uid}"
        # Show their unique referral link
        await query.edit_message_caption(
            caption=(
                f"🎁 **Refer & Earn**\n"
                f"Share your unique link:\n`{ref_link}`\n\n"
                f"Rule: 1 referral = 1 point"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_back")]])
        )

    elif data == "menu_points":
        u = users.find_one({"user_id": uid}) or {}
        pts = u.get("points", 0)
        refs = len(u.get("referrals", []))
        await query.edit_message_caption(
            caption=f"📊 **My Points**\nPoints: **{pts}**\nReferrals: **{refs}**",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_back")]])
        )

    elif data == "menu_withdraw":
        u = users.find_one({"user_id": uid}) or {}
        pts = u.get("points", 0)
        if pts < WITHDRAW_MIN_POINTS:
            await query.edit_message_caption(
                caption=(
                    "💸 **Withdraw Points**\n"
                    f"Minimum {WITHDRAW_MIN_POINTS} points required.\n"
                    f"Your points: **{pts}**"
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_back")]])
            )
            return

        # Ask for details via conversation
        states.update_one(
            {"user_id": uid},
            {"$set": {"state": "await_withdraw_details"}},
            upsert=True
        )
        await query.edit_message_caption(
            caption=(
                "💸 **Withdraw Request**\n"
                "Please send your details in **one message** now:\n"
                "`UPI or contact + points to withdraw`\n\n"
                "Example:\n`UPI: name@bank, Points: 20`"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="menu_back")]])
        )

    elif data == "menu_support":
        await query.edit_message_caption(
            caption="🛟 **Support**\n• For help, message: @YourSupport\n• Typical reply time: within 24 hrs.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_back")]])
        )

    elif data == "menu_how":
        await query.edit_message_caption(
            caption=(
                "📖 **How to Use**\n"
                "1) Join all required channels\n"
                "2) Get your referral link (Refer & Earn)\n"
                "3) Share with friends — each signup gives you 1 point\n"
                "4) View points in *My Points* and request *Withdraw* when eligible\n"
                "5) Use *Redeem Code* for bonus points (if you have a code)"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_back")]])
        )

    elif data == "menu_redeem":
        states.update_one(
            {"user_id": uid},
            {"$set": {"state": "await_redeem_code"}},
            upsert=True
        )
        await query.edit_message_caption(
            caption="🎟️ **Redeem Code**\nPlease send your code now.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="menu_back")]])
        )

    elif data == "menu_back":
        # Return to menu (replace caption & image)
        media = InputMediaPhoto(
            media=WELCOME_IMAGE_URL if WELCOME_IMAGE_URL else "https://picsum.photos/800/400",
            caption="Welcome to **Manu** 🎉\nUse button to navigate 👇",
            parse_mode=ParseMode.MARKDOWN
        )
        try:
            await query.edit_message_media(media=media, reply_markup=main_menu_kb())
        except Exception:
            # fallback if media edit fails
            await send_welcome_menu(update, context)
        # Clear transient states
        states.delete_one({"user_id": uid})

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text replies for Redeem & Withdraw details."""
    if not update.effective_user:
        return
    uid = update.effective_user.id
    st = states.find_one({"user_id": uid})

    if not st:
        return

    state = st.get("state")
    text = (update.message.text or "").strip()

    if state == "await_redeem_code":
        code = text.upper()
        code_doc = redeem_codes.find_one({"code": code})
        if not code_doc:
            await update.message.reply_text("❌ Invalid code. Please try again or tap Back.")
            return

        # multi-use or single-use
        redeemed_by = set(code_doc.get("redeemed_by", []))
        if (not code_doc.get("multi_use", False)) and (uid in redeemed_by):
            await update.message.reply_text("⚠️ You already redeemed this code.")
            return

        pts = int(code_doc.get("points", 0))
        add_point(uid, pts)
        redeem_codes.update_one(
            {"code": code},
            {"$addToSet": {"redeemed_by": uid}}
        )
        users.update_one({"user_id": uid}, {"$inc": {"points": pts}})
        states.delete_one({"user_id": uid})
        await update.message.reply_text(f"✅ Code applied! You received **{pts}** points.")
        return

    if state == "await_withdraw_details":
        # Basic capture; you can enforce stricter parsing
        u = users.find_one({"user_id": uid}) or {}
        pts = u.get("points", 0)
        if pts < WITHDRAW_MIN_POINTS:
            await update.message.reply_text("❌ Not enough points.")
            states.delete_one({"user_id": uid})
            return

        # Heuristic: try to find "Points: N"
        wanted = 0
        import re
        m = re.search(r"(?i)points?\s*[:\-]?\s*(\d+)", text)
        if m:
            wanted = int(m.group(1))
        if wanted <= 0 or wanted > pts:
            wanted = pts  # default withdraw everything available

        withdrawals.insert_one({
            "user_id": uid,
            "points": wanted,
            "contact": text,
            "status": "pending",
            "created_at": datetime.utcnow()
        })
        # Deduct points immediately (or mark as frozen if you prefer)
        users.update_one({"user_id": uid}, {"$inc": {"points": -wanted}})

        states.delete_one({"user_id": uid})
        await update.message.reply_text(
            f"✅ Withdraw request submitted for **{wanted}** points.\nSupport will contact you shortly."
        )

# ===== Admin Commands =====
@admin_only
async def addcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /addcode CODE POINTS [multi]
    Example: /addcode FEST100 10 multi
    """
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addcode CODE POINTS [multi]")
        return
    code = context.args[0].upper()
    try:
        pts = int(context.args[1])
    except:
        await update.message.reply_text("POINTS must be a number.")
        return
    multi = (len(context.args) >= 3 and context.args[2].lower().startswith("multi"))

    redeem_codes.update_one(
        {"code": code},
        {"$set": {"code": code, "points": pts, "multi_use": multi}, "$setOnInsert": {"redeemed_by": []}},
        upsert=True
    )
    await update.message.reply_text(f"✅ Code saved: {code} → {pts} points (multi_use={multi})")

@admin_only
async def setpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /setpoints <user_id> <points>
    """
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /setpoints <user_id> <points>")
        return
    try:
        uid = int(context.args[0]); pts = int(context.args[1])
    except:
        await update.message.reply_text("Both user_id and points must be numbers.")
        return
    ensure_user(uid)
    users.update_one({"user_id": uid}, {"$set": {"points": pts}})
    await update.message.reply_text(f"✅ Set user {uid} points = {pts}")

# ========= App =========
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb_verify_join, pattern="^verify_join$"))
    app.add_handler(CallbackQueryHandler(cb_menu, pattern="^menu_"))

    # Text handler for redeem/withdraw steps
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), on_text))

    # Admin commands
    app.add_handler(CommandHandler("addcode", addcode))
    app.add_handler(CommandHandler("setpoints", setpoints))

    log.info("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
