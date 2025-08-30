from telebot import TeleBot, types
from pymongo import MongoClient
import random

BOT_TOKEN = "8357734886:AAHQi1zmj9q8B__7J-2dyYUWVTQrMRr65Dc"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority"

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

bot = TeleBot(BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client["referral_bot"]
users_collection = db["users"]

# ===== Helper: generate referral link =====
def get_referral_link(user_id):
    return f"https://t.me/YourBotUsername?start={user_id}"

@bot.message_handler(commands=['start'])
def start(message):
    user_name = message.from_user.first_name or "User"

    # Save user in DB
    users_collection.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"name": user_name, "joined": False, "points": 0}},
        upsert=True
    )

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    # 3 join buttons
    for name, url in zip(BUTTON_NAMES, CHANNELS_URLS):
        button = types.InlineKeyboardButton(text=name, url=url)
        keyboard.add(button)
    
    # Check Joined button
    check_button = types.InlineKeyboardButton(text="Check Joined ✅", callback_data="check_join")
    keyboard.add(check_button)
    
    sent_msg = bot.send_photo(
        message.chat.id,
        photo=START_PIC,
        caption=f"HELLO, {user_name}\nYou must join our channels for free access!",
        reply_markup=keyboard
    )

    # Save start message ID for deletion
    users_collection.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"start_msg_id": sent_msg.message_id}}
    )

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
        # Update DB
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"joined": True}}
        )

        # Delete /start message
        user_data = users_collection.find_one({"user_id": user_id})
        if user_data and "start_msg_id" in user_data:
            try:
                bot.delete_message(call.message.chat.id, user_data["start_msg_id"])
            except:
                pass

        # ===== Create Main Menu Buttons =====
        main_menu = types.InlineKeyboardMarkup(row_width=2)

        invite_btn = types.InlineKeyboardButton(
            text="Invite & Earn 2️⃣ Points", 
            url=get_referral_link(user_id)
        )
        points_btn = types.InlineKeyboardButton(
            text="My Points 💰", 
            callback_data="my_points"
        )
        withdraw_btn = types.InlineKeyboardButton(
            text="Withdraw 💵", 
            callback_data="withdraw"
        )
        support_btn = types.InlineKeyboardButton(
            text="Support 🛠️", 
            url="https://t.me/golgibody"
        )
        howto_btn = types.InlineKeyboardButton(
            text="How To Use ❓", 
            callback_data="how_to_use"
        )

        main_menu.add(invite_btn, points_btn)
        main_menu.add(withdraw_btn)
        main_menu.add(support_btn)
        main_menu.add(howto_btn)

        # Send Welcome message with buttons
        bot.send_photo(
            call.message.chat.id,
            photo=WELCOME_PIC,
            caption=f"WELCOME, {user_name}\n~You are on Main Menu\n~Use the buttons below to navigate",
            reply_markup=main_menu
        )

        bot.answer_callback_query(call.id, "✅ You joined all channels!")

    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined all channels.")

# ===== Callback for points, withdraw, how-to =====
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    user_data = users_collection.find_one({"user_id": user_id}) or {"points":0}

    if call.data == "my_points":
        bot.answer_callback_query(call.id, f"💰 You have {user_data.get('points',0)} points.")
    elif call.data == "withdraw":
        if user_data.get("points",0) >= 10:
            bot.answer_callback_query(call.id, "💵 Withdraw request sent!")
            # Reset points after withdraw
            users_collection.update_one({"user_id": user_id}, {"$set":{"points":0}})
        else:
            bot.answer_callback_query(call.id, "❌ Minimum 10 points required for withdrawal.")
    elif call.data == "how_to_use":
        instructions = (
            "📌 How to Use Bot:\n"
            "1. Join all required channels.\n"
            "2. Click 'Invite & Earn Points' to get your referral link.\n"
            "3. Earn 2 points per referral.\n"
            "4. Click 'My Points' to see your points.\n"
            "5. Click 'Withdraw' to redeem points (min 10 points).\n"
            "6. For support, click 'Support' button."
        )
        bot.answer_callback_query(call.id, instructions, show_alert=True)

bot.polling()
