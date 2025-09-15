from telebot import TeleBot, types
from pymongo import MongoClient
from datetime import datetime

# ==================== CONFIG ====================
BOT_TOKEN = "8355581502:AAEawyUncPofLQVzLS_ibLN4WkF8wPa3lVo"
MONGO_URI = "mongodb+srv://TRUSTLYTRANSACTIONBOT:TRUSTLYTRANSACTIONBOT@cluster0.t60mxb7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_USERNAME = "Inquiry_chatbot"

OWNER_ID = 6998916494  # <-- Apna Telegram ID yaha daal do

# ✅ Ab sirf 1 hi channel rakha gaya
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
        types.InlineKeyboardButton(text="Deposit Balance ⚖️", callback_data="deposit_balance")  # ✅ NEW BUTTON
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
            "points": 0
        })
    else:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"username": username, "name": user_name}}
        )

    # Referral system (🔹 updated: points remove kar diye)
    if not existing_user and len(args) > 1:
        try:
            referrer_id = int(args[1])
            if referrer_id != user_id:
                referrer = users_collection.find_one({"user_id": referrer_id})
                if referrer:
                    users_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {"referrer_id": referrer_id}}
                    )

                    # ✅ Sirf referral ka notification jayega OWNER ko
                    bot.send_message(
                        OWNER_ID,
                        f"👤 New Referral!\n"
                        f"User: {user_name} (@{username})\n"
                        f"Referred by: {referrer.get('name')} (@{referrer.get('username')})"
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

# ===== (Baaki saara code same h - withdrawal, admin panel etc.) =====

# ==================== POLLING ====================
bot.polling()
