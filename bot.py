from telebot import TeleBot, types
from pymongo import MongoClient
from datetime import datetime

# ==================== CONFIG ====================
BOT_TOKEN = "8355581502:AAEawyUncPofLQVzLS_ibLN4WkF8wPa3lVo"
MONGO_URI = "mongodb+srv://TRUSTLYTRANSACTIONBOT:TRUSTLYTRANSACTIONBOT@cluster0.t60mxb7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_USERNAME = "Inquiry_chatbot"

OWNER_ID = 6998916494  # <-- Apna Telegram ID yaha daal do

CHANNELS_URLS = [
    "https://t.me/Trade_With_Gaorav"
]

BUTTON_NAMES = [
    "Join channel"
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
        types.InlineKeyboardButton(text="Invite & Earn commission", callback_data="invite"),
        types.InlineKeyboardButton(text="My Points 💰", callback_data="my_points")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="👥 My Team", callback_data="my_team"),
        types.InlineKeyboardButton(text="Commission", callback_data="commission")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="Withdraw 💵", callback_data="withdraw"),
        types.InlineKeyboardButton(text="Deposit Balance ⚖️", callback_data="deposit_balance")
    )
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

    # ✅ Referral ID extract
    referrer_id = None
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
        except:
            referrer_id = None

    if not existing_user:
        new_user = {
            "user_id": user_id,
            "name": user_name,
            "username": username,
            "joined": False,
            "points": 0
        }
        if referrer_id and referrer_id != user_id:
            new_user["referrer_id"] = referrer_id

            # ✅ Referrer ka data fetch
            referrer_data = users_collection.find_one({"user_id": referrer_id})
            referrer_name = referrer_data.get("name", "Unknown") if referrer_data else "Unknown"
            referrer_username = (
                f"@{referrer_data.get('username')}" if referrer_data and referrer_data.get("username") else "N/A"
            )

            # ✅ Owner ko notification
            bot.send_message(
                OWNER_ID,
                f"📢 New Referral!\n"
                f"👤 User: {user_name} (@{username})\n"
                f"➡️ Referred by: {referrer_name} ({referrer_username})"
            )

        users_collection.insert_one(new_user)
    else:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"username": username, "name": user_name}}
        )

    # ===== Channels join check =====
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

# ===== All Referrals Command (Owner Only) =====
@bot.message_handler(commands=['Allrefrals'])
def all_referrals(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return

    users = list(users_collection.find({}))
    if not users:
        bot.send_message(OWNER_ID, "❌ No users found in the database.")
        return

    report_lines = ["📢 All Referrals Report\n"]
    for user in users:
        user_id = user["user_id"]
        name = user.get("name", "Unknown")
        username = f"@{user['username']}" if user.get("username") else "N/A"

        referrals = list(users_collection.find({"referrer_id": user_id}))
        referral_count = len(referrals)

        # Main user line
        report_lines.append(f"👤 {username} ({name}) → {referral_count} referrals")

        # Show referred users list
        if referral_count > 0:
            for ref in referrals:
                ref_name = ref.get("name", "User")
                ref_username = f"@{ref['username']}" if ref.get("username") else ref_name
                report_lines.append(f"   • {ref_username}")

        report_lines.append("")  # Blank line for spacing

    report_text = "\n".join(report_lines)
    bot.send_message(OWNER_ID, report_text)

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
    user_data = users_collection.find_one({"user_id": user_id}) or {"points": 0}

    if call.data == "invite":
        referral_link = get_referral_link(user_id)
        points = user_data.get("points", 0)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"📢 Your Referral Link:\n`{referral_link}`\n\n💰 Your Points: {points}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    elif call.data == "my_points":
        points = user_data.get("points", 0)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"💰 Your Current Points: {points}",
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
        points = user_data.get("points", 0)
        team_list = "\n".join(usernames) if usernames else "No referrals yet."
        msg = (
            f"👥 Your Team: {count} members\n\n"
            f"{team_list}\n\n"
            f"💰 Your Balance: {points} points"
        )
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=msg,
            reply_markup=keyboard
        )

    elif call.data == "commission":
        referrals = list(users_collection.find({"referrer_id": user_id}))
        count = len(referrals)

        usernames = []
        for r in referrals:
            if r.get("username"):
                usernames.append("@" + r["username"])
            else:
                usernames.append(r.get("name", "User"))

        # ✅ Commission points fix 0 rakha
        commission_points = 0
        team_list = "\n".join(usernames) if usernames else "No referrals yet."

        msg = (
            f"⚡ Commission Report ⚡\n\n"
            f"👥 Total Referrals: {count}\n"
            f"💰 Earned from Referrals: {commission_points} points\n\n"
            f"👤 Referral Users:\n{team_list}\n\n"
            f"⚠️ Note: Commission is just a report. Withdrawals are only from your Points balance."
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
        points = user_data.get("points", 0)
        if points < 10:
            bot.answer_callback_query(call.id, "❌ Minimum 10 points required for withdrawal.")
            return
        msg = bot.send_message(call.message.chat.id,
            f"💵 You have {points} points.\nSend the amount you want to withdraw (min 1000 points):")
        bot.register_next_step_handler(msg, process_withdraw)

    elif call.data == "deposit_balance":
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption="For Deposit Detail Message Here👉👉 @Trader_Gaurav_official",
            reply_markup=keyboard
        )

    elif call.data == "support":
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption="If you are facing any problem Contact Support : @Trader_Gaurav_official",
            reply_markup=keyboard
        )

    elif call.data == "how_to_use":
        instructions = (
            "📌 How to Use Bot:\n\n"
            "1. Join all required channels.\n"
            "2. Click 'Invite & Earn Commission ' to get your referral link..\n"
            "3. Referral se points abhi 0 hain (sirf tracking ke liye).\n"
            "4. Click 'My team' to see your invited members.\n"
            "5. Click 'Withdraw' to redeem Balance (min 10 points)..\n"
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
            types.InlineKeyboardButton(text="➕ Add Points", callback_data="admin_add_points"),
            types.InlineKeyboardButton(text="➖ Remove Points", callback_data="admin_remove_points"),
            types.InlineKeyboardButton(text="👁‍🗨 Check User Points", callback_data="admin_check_points"),
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

        if call.data == "admin_add_points":
            msg = bot.send_message(call.message.chat.id, "Send in this format:\n<user_id> <points> to ADD")
            bot.register_next_step_handler(msg, lambda m: process_admin_points(m, "add"))

        elif call.data == "admin_remove_points":
            msg = bot.send_message(call.message.chat.id, "Send in this format:\n<user_id> <points> to REMOVE")
            bot.register_next_step_handler(msg, lambda m: process_admin_points(m, "remove"))

        elif call.data == "admin_check_points":
            msg = bot.send_message(call.message.chat.id, "Send <user_id> to check points")
            bot.register_next_step_handler(msg, process_admin_check_points)

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
    user_data = users_collection.find_one({"user_id": user_id}) or {"points": 0}
    total_points = user_data.get("points", 0)

    try:
        withdraw_amount = int(message.text)
        if withdraw_amount < 1000:
            bot.reply_to(message, "❌ Minimum 1000 points required to withdraw.")
            return
        if withdraw_amount > total_points:
            bot.reply_to(message, f"❌ You only have {total_points} points. Enter a valid amount.")
            return

        users_collection.update_one({"user_id": user_id}, {"$inc": {"points": -withdraw_amount}})
        withdraw_collection.insert_one({
            "user_id": user_id,
            "points": withdraw_amount,
            "date": datetime.utcnow()
        })

        remaining = total_points - withdraw_amount
        bot.reply_to(
            message,
            f"✅ Withdraw successful! {withdraw_amount} points withdrawn.\n"
            f"Remaining points: {remaining}\n\n"
            f"🛠️ Contact Support: @Trader_Gaurav_official dm with your upi id !!"
        )

        bot.send_message(
            OWNER_ID,
            f"📢 Withdraw Request!\n"
            f"👤 User: {username} (ID: {user_id})\n"
            f"💵 Amount: {withdraw_amount} points\n"
            f"💰 Remaining Balance: {remaining}"
        )

    except:
        bot.reply_to(message, "❌ Invalid input! Send numeric amount only.")

# ===== Admin Step Handlers =====
def process_admin_points(message, action):
    try:
        user_id, points = map(int, message.text.split())
        if action == "add":
            result = users_collection.update_one({"user_id": user_id}, {"$inc": {"points": points}})
            if result.matched_count:
                bot.reply_to(message, f"✅ Added {points} points to user {user_id}")
            else:
                bot.reply_to(message, "❌ User not found")
        elif action == "remove":
            result = users_collection.update_one({"user_id": user_id}, {"$inc": {"points": -points}})
            if result.matched_count:
                bot.reply_to(message, f"✅ Removed {points} points from user {user_id}")
            else:
                bot.reply_to(message, "❌ User not found")
    except:
        bot.reply_to(message, "❌ Format error! Use <user_id> <points>")

def process_admin_check_points(message):
    try:
        user_id = int(message.text)
        user_data = users_collection.find_one({"user_id": user_id})
        if user_data:
            bot.reply_to(message, f"💰 User {user_id} has {user_data.get('points', 0)} points")
        else:
            bot.reply_to(message, "❌ User not found")
    except:
        bot.reply_to(message, "❌ Format error! Send <user_id>")

# ==================== POLLING ====================
bot.polling()
