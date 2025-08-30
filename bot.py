from telebot import TeleBot, types
from pymongo import MongoClient

BOT_TOKEN = "8357734886:AAHQi1zmj9q8B__7J-2dyYUWVTQrMRr65Dc"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"  # Optional, agar data save karna ho

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

bot = TeleBot(BOT_TOKEN)

# Optional: MongoDB setup
client = MongoClient(MONGO_URI)
db = client["referral_bot"]
users_collection = db["users"]

@bot.message_handler(commands=['start'])
def start(message):
    user_name = message.from_user.first_name or "User"
    
    # Save user in DB
    users_collection.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"name": user_name, "joined": False}},
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
    
    sent_msg = bot.send_message(
        message.chat.id,
        f"HELLO, {user_name}\nYoU MUST NEED To JoIN OUR CHANNELS FOR FREE ACCOUNTS!!!",
        reply_markup=keyboard
    )
    
    # Save start message ID for deletion
    users_collection.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"start_msg_id": sent_msg.message_id}}
    )

# Callback for Check Joined
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
        
        # Send Welcome message
        bot.send_message(
            call.message.chat.id,
            f"WELCOME, {user_name}\n~YoU ARE ON MAIN MENU\n~UsE BELOW BUTTONS To NAVIGATE"
        )
        
        bot.answer_callback_query(call.id, "✅ You joined all channels!")
    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined all channels.")

bot.polling()
