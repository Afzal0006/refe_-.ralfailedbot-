from telebot import TeleBot, types
from pymongo import MongoClient
from datetime import datetime

# ==================== CONFIG ====================
BOT_TOKEN = "7643831340:AAGieuPJND4MekAutSf3xzta1qdoKo5mbZU"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_USERNAME = "MusafirMmBot"
OWNER_ID = 6998916494  # <-- Apna Telegram ID yaha daal do

CHANNELS_URLS = [
    "https://t.me/guiii8889",
    "https://t.me/SexyEmoji"
]

BUTTON_NAMES = [
    "Join channel",
    "🎯 Join Fun Channel"
]

START_PIC = "https://i.ibb.co/8DLsQxtn/x.jpg"
WELCOME_PIC = "https://i.ibb.co/zhgphkVb/x.jpg"

# ==================== INIT ====================
bot = TeleBot(BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client["referral_bot"]
users_collection = db["users"]
withdraw_collection = db["withdraw_history"]

# ===== Helper Functions =====
def get_referral_link(user_id):
    return f"https://t.me/{BOT_USERNAME}?start={user_id}"

def main_menu_keyboard(user_id):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="Invite & Earn Points", callback_data="invite"),
        types.InlineKeyboardButton(text="My Wallet 💰", callback_data="my_points")
    )
    keyboard.add(types.InlineKeyboardButton(text="👥 My Team", callback_data="my_team"))
    keyboard.add(types.InlineKeyboardButton(text="Withdraw 💵", callback_data="withdraw"))
    keyboard.add(types.InlineKeyboardButton(text="Support 🛠️", callback_data="support"))
    keyboard.add(types.InlineKeyboardButton(text="How To Use ❓", callback_data="how_to_use"))
    if OWNER_ID:
        keyboard.add(types.InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="admin_panel"))
    return keyboard

# ===== Start Command =====
@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"
    username = message.from_user.username

    existing_user = users_collection.find_one({"user_id": user_id})

    if not existing_user:
        users_collection.insert_one({
            "user_id": user_id,
            "name": user_name,
            "username": username,
            "joined": False,
            "wallet": 0,
            "referrals": 0,
            "referred_by": None
        })
    else:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"username": username, "name": user_name}}
        )

    # Referral system
    if not existing_user and len(args) > 1:
        try:
            referrer_id = int(args[1])
            if referrer_id != user_id:
                referrer = users_collection.find_one({"user_id": referrer_id})
                if referrer:
                    users_collection.update_one(
                        {"user_id": referrer_id},
                        {"$inc": {"wallet": 2, "referrals": 1}}
                    )
                    new_wallet = referrer.get("wallet", 0) + 2
                    bot.send_message(referrer_id, f"🎉 You earned 2 points!\nNow your wallet balance: {new_wallet}")
                    bot.send_message(
                        OWNER_ID,
                        f"👤 New Referral!\nUser: {user_name} (@{username})\nReferred by: {referrer.get('name')} (@{referrer.get('username')})\nNew wallet: {new_wallet}"
                    )
                    users_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {"referred_by": referrer_id}}
                    )
        except Exception as e:
            print("Referral error:", e)

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for name, url in zip(BUTTON_NAMES, CHANNELS_URLS):
        keyboard.add(types.InlineKeyboardButton(text=name, url=url))
    keyboard.add(types.InlineKeyboardButton(text="Check Joined ✅", callback_data="check_join"))

    sent_msg = bot.send_photo(
        message.chat.id,
        photo=START_PIC,
        caption=f"HELLO, {user_name}\nYou must join our channels for free access!",
        reply_markup=keyboard
    )

    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"start_msg_id": sent_msg.message_id}}
    )

# ===== Check Join Callback =====
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    user_id = call.from_user.id
    user_name = call.from_user.first_name or "User"
    joined_all = True

    for url in CHANNELS_URLS:
        username = url.split('/')[-1]
        try:
            member = bot.get_chat_member(f"@{username}", user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                joined_all = False
                break
        except:
            joined_all = False
            break

    if joined_all:
        users_collection.update_one({"user_id": user_id}, {"$set": {"joined": True}})
        user_data = users_collection.find_one({"user_id": user_id})
        if user_data and "start_msg_id" in user_data:
            try:
                bot.delete_message(call.message.chat.id, user_data["start_msg_id"])
            except:
                pass

        bot.send_photo(
            call.message.chat.id,
            photo=WELCOME_PIC,
            caption=f"WELCOME, {user_name}\n~You are on Main Menu\n~Use the buttons below to navigate",
            reply_markup=main_menu_keyboard(user_id)
        )
        bot.answer_callback_query(call.id, "✅ You joined all channels!")
    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined all channels.")

# ===== Main Callback Handler =====
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    user_data = users_collection.find_one({"user_id": user_id}) or {"wallet": 0, "referrals": 0}

    if call.data == "invite":
        referral_link = get_referral_link(user_id)
        wallet = user_data.get("wallet", 0)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"📢 Your Referral Link:\n`{referral_link}`\n\n💰 Your Wallet Balance: {wallet}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    elif call.data == "my_points":
        wallet = user_data.get("wallet", 0)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"💰 Your Current Wallet Balance: {wallet}",
            reply_markup=keyboard
        )

    elif call.data == "my_team":
        referrals = user_data.get("referrals", 0)
        wallet = user_data.get("wallet", 0)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"👥 You referred {referrals} users.\n💰 Your Wallet Balance: {wallet}",
            reply_markup=keyboard
        )

    elif call.data == "withdraw":
        wallet = user_data.get("wallet", 0)
        if wallet < 10:
            bot.answer_callback_query(call.id, "❌ Minimum 10 points required for withdrawal.")
            return
        msg = bot.send_message(call.message.chat.id, f"💵 You have {wallet} points.\nSend the amount you want to withdraw (min 10 points):")
        bot.register_next_step_handler(msg, process_withdraw)

    elif call.data == "support":
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption="🛠️ Contact Support: @golgibody",
            reply_markup=keyboard
        )

    elif call.data == "how_to_use":
        instructions = (
            "📌 How to Use Bot:\n\n"
            "1. Join all required channels.\n"
            "2. Click 'Invite & Earn Points' to get your referral link.\n"
            "3. Earn 2 points per referral.\n"
            "4. Check wallet anytime.\n"
            "5. Withdraw minimum 10 points.\n"
            "6. Contact support if needed."
        )
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=instructions,
            reply_markup=keyboard
        )

    elif call.data == "back_to_main":
        user_name = call.from_user.first_name or "User"
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"WELCOME, {user_name}\n~You are on Main Menu\n~Use the buttons below to navigate",
            reply_markup=main_menu_keyboard(user_id)
        )

# ===== Withdraw Step Handler =====
def process_withdraw(message):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    user_data = users_collection.find_one({"user_id": user_id}) or {"wallet": 0}
    total_wallet = user_data.get("wallet", 0)

    try:
        withdraw_amount = int(message.text)
        if withdraw_amount < 10:
            bot.reply_to(message, "❌ Minimum 10 points required to withdraw.")
            return
        if withdraw_amount > total_wallet:
            bot.reply_to(message, f"❌ You only have {total_wallet} points. Enter a valid amount.")
            return

        users_collection.update_one({"user_id": user_id}, {"$inc": {"wallet": -withdraw_amount}})
        withdraw_collection.insert_one({
            "user_id": user_id,
            "points": withdraw_amount,
            "date": datetime.utcnow()
        })

        remaining = total_wallet - withdraw_amount
        bot.reply_to(
            message,
            f"✅ Withdraw successful! {withdraw_amount} points withdrawn.\nRemaining wallet: {remaining}\n\n🛠️ Contact Support: @golgibody with your UPI ID."
        )

        bot.send_message(
            OWNER_ID,
            f"📢 Withdraw Request!\n👤 User: {username} (ID: {user_id})\n💵 Amount: {withdraw_amount} points\n💰 Remaining Wallet: {remaining}"
        )

    except:
        bot.reply_to(message, "❌ Invalid input! Send numeric amount only.")

# ===== NEW COMMAND: /add =====
@bot.message_handler(commands=['add'])
def add_wallet(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Not authorized.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "❌ Format: /add <username or user_id> <amount>")
            return

        target = parts[1]
        amount = int(parts[2])

        if target.startswith("@"):
            user_data = users_collection.find_one({"username": target[1:]})
        else:
            try:
                target_id = int(target)
                user_data = users_collection.find_one({"user_id": target_id})
            except:
                user_data = None

        if not user_data:
            bot.reply_to(message, "❌ User not found.")
            return

        users_collection.update_one({"user_id": user_data["user_id"]}, {"$inc": {"wallet": amount}})
        bot.reply_to(message, f"✅ Added {amount} to {user_data.get('name', 'Unknown')} (@{user_data.get('username', '-')}) wallet.")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}\nUse: /add <username or user_id> <amount>")

# ==================== POLLING ====================
bot.polling()
