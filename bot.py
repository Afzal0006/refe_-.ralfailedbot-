from telebot import TeleBot, types
from pymongo import MongoClient
from datetime import datetime

# ==================== CONFIG ====================
BOT_TOKEN = "8357734886:AAHQi1zmj9q8B__7J-2dyYUWVTQrMRr65Dc"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority"
BOT_USERNAME = "Eeuei8w9w9wbbot"  # <-- apne bot ka username (without @)

CHANNELS_URLS = [
    "https://t.me/guiii8889",
    "https://t.me/testing7889gy",
    "https://t.me/SexyEmoji"
]

BUTTON_NAMES = [
    "Join channel",
    "💎 Join VIP Channel",
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

# ===== Helper: generate referral link =====
def get_referral_link(user_id):
    return f"https://t.me/{BOT_USERNAME}?start={user_id}"

# ===== Main Menu Buttons =====
def main_menu_keyboard(user_id):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="Invite & Earn Points", callback_data="invite"),
        types.InlineKeyboardButton(text="My Points 💰", callback_data="my_points")
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
    return keyboard

# ===== Start Command =====
@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"

    existing_user = users_collection.find_one({"user_id": user_id})

    if not existing_user:
        users_collection.insert_one({
            "user_id": user_id,
            "name": user_name,
            "joined": False,
            "points": 0
        })

        if len(args) > 1:
            try:
                referrer_id = int(args[1])
                if referrer_id != user_id:
                    referrer = users_collection.find_one({"user_id": referrer_id})
                    if referrer:
                        users_collection.update_one(
                            {"user_id": referrer_id},
                            {"$inc": {"points": 2}}
                        )
                        new_points = referrer.get("points", 0) + 2
                        bot.send_message(
                            referrer_id,
                            f"🎉 You earned 2 points!\nNow you have {new_points} points."
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
    user_data = users_collection.find_one({"user_id": user_id}) or {"points":0}

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
        points = user_data.get("points",0)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"💰 Your Current Points: {points}",
            reply_markup=keyboard
        )

    elif call.data == "withdraw":
        points = user_data.get("points",0)
        if points >= 10:
            withdraw_collection.insert_one({
                "user_id": user_id,
                "points": points,
                "date": datetime.utcnow()
            })
            users_collection.update_one({"user_id": user_id}, {"$set":{"points":0}})

            bot.answer_callback_query(call.id, f"💵 Withdraw request sent!\nPoints withdrawn: {points}")
        else:
            bot.answer_callback_query(call.id, "❌ Minimum 10 points required for withdrawal.")

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
            "4. Click 'My Points' to see your points.\n"
            "5. Click 'Withdraw' to redeem points (min 10 points).\n"
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

    elif call.data == "back_to_main":
        user_name = call.from_user.first_name or "User"
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"WELCOME, {user_name}\n~You are on Main Menu\n~Use the buttons below to navigate",
            reply_markup=main_menu_keyboard(user_id)
        )

bot.polling()
