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
        types.InlineKeyboardButton(text="Invite & Earn", callback_data="invite"),
        types.InlineKeyboardButton(text="My Team 👥", callback_data="my_team")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="Commission 💰", callback_data="commission"),
        types.InlineKeyboardButton(text="Balance 🏦", callback_data="balance")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="Withdraw 💵", callback_data="withdraw")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="Support 🛠️", callback_data="support")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="How To Use ❓", callback_data="how_to_use")
    )
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
            "commission": 0,
            "balance": 0,
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
                        {"$inc": {"commission": 2}}
                    )
                    users_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {"referred_by": referrer_id}}
                    )
                    new_commission = referrer.get("commission", 0) + 2
                    bot.send_message(
                        referrer_id,
                        f"🎉 You earned 2 commission!\nNow you have {new_commission} commission."
                    )
                    bot.send_message(
                        OWNER_ID,
                        f"👤 New Referral!\n"
                        f"User: {user_name} (@{username})\n"
                        f"Referred by: {referrer.get('name')} (@{referrer.get('username')})\n"
                        f"Referrer new commission: {new_commission}"
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
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"joined": True}}
        )

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
    user_data = users_collection.find_one({"user_id": user_id}) or {"commission": 0, "balance": 0}

    if call.data == "invite":
        referral_link = get_referral_link(user_id)
        commission = user_data.get("commission", 0)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"📢 Your Referral Link:\n`{referral_link}`\n\n💰 Your Commission: {commission}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    elif call.data == "my_team":
        referrals = users_collection.count_documents({"referred_by": user_id})
        commission = user_data.get("commission", 0)
        balance = user_data.get("balance", 0)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"👥 Your Team: {referrals} members\n💰 Commission: {commission}\n🏦 Balance: {balance}",
            reply_markup=keyboard
        )

    elif call.data == "commission":
        commission = user_data.get("commission", 0)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"💰 Your Commission: {commission}",
            reply_markup=keyboard
        )

    elif call.data == "balance":
        balance = user_data.get("balance", 0)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"🏦 Your Balance: {balance}",
            reply_markup=keyboard
        )

    elif call.data == "withdraw":
        commission = user_data.get("commission", 0)
        if commission < 10:
            bot.answer_callback_query(call.id, "❌ Minimum 10 commission required for withdrawal.")
            return
        msg = bot.send_message(call.message.chat.id,
            f"💵 You have {commission} commission.\nSend the amount you want to withdraw (min 10):")
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
            "2. Click 'Invite & Earn' to get your referral link.\n"
            "3. Earn 2 commission per referral.\n"
            "4. Use 'My Team' to check your referrals.\n"
            "5. Check 'Balance' (admin adds it).\n"
            "6. Withdraw minimum 10 commission.\n"
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

    # ===== Admin Panel =====
    elif call.data == "admin_panel":
        if call.from_user.id != OWNER_ID:
            bot.answer_callback_query(call.id, "❌ You are not authorized.")
            return

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton(text="➕ Add Balance", callback_data="admin_add_balance"),
            types.InlineKeyboardButton(text="👁‍🗨 Check User", callback_data="admin_check_user"),
            types.InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="back_to_main")
        )

        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption="⚙️ Admin Panel - Choose an action:",
            reply_markup=keyboard
        )

    elif call.data.startswith("admin_"):
        if call.from_user.id != OWNER_ID:
            bot.answer_callback_query(call.id, "❌ You are not authorized.")
            return

        if call.data == "admin_add_balance":
            msg = bot.send_message(call.message.chat.id, "Send in this format:\n<user_id> <amount>")
            bot.register_next_step_handler(msg, process_admin_add_balance)

        elif call.data == "admin_check_user":
            msg = bot.send_message(call.message.chat.id, "Send <user_id> to check commission & balance")
            bot.register_next_step_handler(msg, process_admin_check_user)

# ===== Withdraw Step Handler =====
def process_withdraw(message):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    user_data = users_collection.find_one({"user_id": user_id}) or {"commission": 0}
    total_commission = user_data.get("commission", 0)

    try:
        withdraw_amount = int(message.text)
        if withdraw_amount < 10:
            bot.reply_to(message, "❌ Minimum 10 commission required to withdraw.")
            return
        if withdraw_amount > total_commission:
            bot.reply_to(message, f"❌ You only have {total_commission}. Enter a valid amount.")
            return

        users_collection.update_one({"user_id": user_id}, {"$inc": {"commission": -withdraw_amount}})
        withdraw_collection.insert_one({
            "user_id": user_id,
            "commission": withdraw_amount,
            "date": datetime.utcnow()
        })

        remaining = total_commission - withdraw_amount
        bot.reply_to(
            message,
            f"✅ Withdraw successful! {withdraw_amount} commission withdrawn.\n"
            f"Remaining commission: {remaining}\n\n"
            f"🛠️ Contact Support: @golgibody dm with your upi id !!"
        )

        bot.send_message(
            OWNER_ID,
            f"📢 Withdraw Request!\n"
            f"👤 User: {username} (ID: {user_id})\n"
            f"💵 Amount: {withdraw_amount}\n"
            f"💰 Remaining Commission: {remaining}"
        )

    except:
        bot.reply_to(message, "❌ Invalid input! Send numeric amount only.")

# ===== Admin Step Handlers =====
def process_admin_add_balance(message):
    try:
        user_id, amount = map(int, message.text.split())
        result = users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})
        if result.matched_count:
            bot.reply_to(message, f"✅ Added {amount} balance to user {user_id}")
        else:
            bot.reply_to(message, "❌ User not found")
    except:
        bot.reply_to(message, "❌ Format error! Use <user_id> <amount>")

def process_admin_check_user(message):
    try:
        user_id = int(message.text)
        user_data = users_collection.find_one({"user_id": user_id})
        if user_data:
            bot.reply_to(message, f"💰 User {user_id}\nCommission: {user_data.get('commission', 0)}\nBalance: {user_data.get('balance', 0)}")
        else:
            bot.reply_to(message, "❌ User not found")
    except:
        bot.reply_to(message, "❌ Format error! Send <user_id>")

# ==================== POLLING ====================
bot.polling(none_stop=True, timeout=60)
