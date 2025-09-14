from telebot import TeleBot, types
from pymongo import MongoClient
from datetime import datetime

# ==================== CONFIG ====================
BOT_TOKEN = "8357734886:AAHQi1zmj9q8B__7J-2dyYUWVTQrMRr65Dc"
MONGO_URI = "mongodb+srv://TRUSTLYTRANSACTIONBOT:TRUSTLYTRANSACTIONBOT@cluster0.t60mxb7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_USERNAME = "Eeuei8w9w9wbbot"

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
        types.InlineKeyboardButton(text="Invite & Earn ⚖️ Balance", callback_data="invite"),
        types.InlineKeyboardButton(text="My Balance ⚖️", callback_data="my_balance")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="👥 My Team", callback_data="my_team"),
        types.InlineKeyboardButton(text="Cummins", callback_data="cummins")
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
            "balance": 0
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
                        {"$inc": {"balance": 2}}
                    )
                    new_balance = referrer.get("balance", 0) + 2

                    # 🔥 Save referrer_id in new user
                    users_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {"referrer_id": referrer_id}}
                    )

                    bot.send_message(
                        referrer_id,
                        f"🎉 You earned 2 ⚖️ balance!\nNow you have {new_balance} balance."
                    )
                    bot.send_message(
                        OWNER_ID,
                        f"👤 New Referral!\n"
                        f"User: {user_name} (@{username})\n"
                        f"Referred by: {referrer.get('name')} (@{referrer.get('username')})\n"
                        f"Referrer new balance: {new_balance}"
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

# ===== Main Callback Handler =====
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    user_data = users_collection.find_one({"user_id": user_id}) or {"balance": 0}

    if call.data == "invite":
        referral_link = get_referral_link(user_id)
        balance = user_data.get("balance", 0)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"📢 Your Referral Link:\n`{referral_link}`\n\n⚖️ Your Balance: {balance}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    elif call.data == "my_balance":
        balance = user_data.get("balance", 0)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"⚖️ Your Current Balance: {balance}",
            reply_markup=keyboard
        )

    elif call.data == "my_team":
        referrals = list(users_collection.find({"referrer_id": user_id}))
        count = len(referrals)
        usernames = []
        for r in referrals:
            if r.get("username"):
                usernames.append("@" + r["username"])
            else:
                usernames.append(r.get("name", "User"))
        balance = user_data.get("balance", 0)
        team_list = "\n".join(usernames) if usernames else "No referrals yet."
        msg = (
            f"👥 Your Team: {count} members\n\n"
            f"{team_list}\n\n"
            f"⚖️ Your Balance: {balance}"
        )
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=msg,
            reply_markup=keyboard
        )

    elif call.data == "cummins":
        referrals = list(users_collection.find({"referrer_id": user_id}))
        count = len(referrals)

        usernames = []
        for r in referrals:
            if r.get("username"):
                usernames.append("@" + r["username"])
            else:
                usernames.append(r.get("name", "User"))

        cummins_balance = count * 2
        team_list = "\n".join(usernames) if usernames else "No referrals yet."

        msg = (
            f"⚡ Cummins Report ⚡\n\n"
            f"👥 Total Referrals: {count}\n"
            f"⚖️ Cummins Balance: {cummins_balance}\n\n"
            f"👤 Referral Users:\n{team_list}"
        )

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))

        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=msg,
            reply_markup=keyboard
        )

    elif call.data == "withdraw":
        balance = user_data.get("balance", 0)
        if balance < 10:
            bot.answer_callback_query(call.id, "❌ Minimum 10 ⚖️ balance required for withdrawal.")
            return
        msg = bot.send_message(call.message.chat.id,
            f"💵 You have {balance} balance.\nSend the amount you want to withdraw (min 10 ⚖️):")
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
            "2. Click 'Invite & Earn ⚖️ Balance' to get your referral link.\n"
            "3. Earn 2 ⚖️ balance per referral.\n"
            "4. Click 'My Balance' to see your balance.\n"
            "5. Click 'Withdraw' to redeem balance (min 10 ⚖️).\n"
            "6. For support, click 'Support' button."
        )
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=instructions,
            reply_markup=keyboard
        )

    elif call.data == "admin_panel":
        if call.from_user.id != OWNER_ID:
            bot.answer_callback_query(call.id, "❌ You are not authorized.")
            return

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton(text="➕ Add Balance", callback_data="admin_add_balance"),
            types.InlineKeyboardButton(text="➖ Remove Balance", callback_data="admin_remove_balance"),
            types.InlineKeyboardButton(text="👁‍🗨 Check User Balance", callback_data="admin_check_balance"),
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
            msg = bot.send_message(call.message.chat.id, "Send in this format:\n<user_id> <balance> to ADD")
            bot.register_next_step_handler(msg, lambda m: process_admin_balance(m, "add"))

        elif call.data == "admin_remove_balance":
            msg = bot.send_message(call.message.chat.id, "Send in this format:\n<user_id> <balance> to REMOVE")
            bot.register_next_step_handler(msg, lambda m: process_admin_balance(m, "remove"))

        elif call.data == "admin_check_balance":
            msg = bot.send_message(call.message.chat.id, "Send <user_id> to check balance")
            bot.register_next_step_handler(msg, process_admin_check_balance)

# ===== Withdraw Step Handler =====
def process_withdraw(message):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    user_data = users_collection.find_one({"user_id": user_id}) or {"balance": 0}
    total_balance = user_data.get("balance", 0)

    try:
        withdraw_amount = int(message.text)
        if withdraw_amount < 10:
            bot.reply_to(message, "❌ Minimum 10 ⚖️ balance required to withdraw.")
            return
        if withdraw_amount > total_balance:
            bot.reply_to(message, f"❌ You only have {total_balance} balance. Enter a valid amount.")
            return

        users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": -withdraw_amount}})
        withdraw_collection.insert_one({
            "user_id": user_id,
            "balance": withdraw_amount,
            "date": datetime.utcnow()
        })

        remaining = total_balance - withdraw_amount
        bot.reply_to(
            message,
            f"✅ Withdraw successful! {withdraw_amount} ⚖️ withdrawn.\n"
            f"Remaining balance: {remaining}\n\n"
            f"🛠️ Contact Support: @golgibody dm with your upi id !!"
        )

        bot.send_message(
            OWNER_ID,
            f"📢 Withdraw Request!\n"
            f"👤 User: {username} (ID: {user_id})\n"
            f"💵 Amount: {withdraw_amount} ⚖️\n"
            f"⚖️ Remaining Balance: {remaining}"
        )

    except:
        bot.reply_to(message, "❌ Invalid input! Send numeric amount only.")

# ===== Admin Step Handlers =====
def process_admin_balance(message, action):
    try:
        user_id, balance = map(int, message.text.split())
        if action == "add":
            result = users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": balance}})
            if result.matched_count:
                bot.reply_to(message, f"✅ Added {balance} ⚖️ to user {user_id}")
            else:
                bot.reply_to(message, "❌ User not found")
        elif action == "remove":
            result = users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": -balance}})
            if result.matched_count:
                bot.reply_to(message, f"✅ Removed {balance} ⚖️ from user {user_id}")
            else:
                bot.reply_to(message, "❌ User not found")
    except:
        bot.reply_to(message, "❌ Format error! Use <user_id> <balance>")

def process_admin_check_balance(message):
    try:
        user_id = int(message.text)
        user_data = users_collection.find_one({"user_id": user_id})
        if user_data:
            bot.reply_to(message, f"⚖️ User {user_id} has {user_data.get('balance', 0)} balance")
        else:
            bot.reply_to(message, "❌ User not found")
    except:
        bot.reply_to(message, "❌ Format error! Send <user_id>")

# ==================== POLLING ====================
bot.polling()
