from telebot import TeleBot, types

# ===== Config =====
BOT_TOKEN = "8357734886:AAHQi1zmj9q8B__7J-2dyYUWVTQrMRr65Dc"

# 3 Channels
CHANNELS = ["@testing7889gy", "@testing7889gy", "@testing7889gy"]

bot = TeleBot(BOT_TOKEN)

# /start command
@bot.message_handler(commands=['start'])
def start(message):
    keyboard = types.InlineKeyboardMarkup(row_width=2)  # row_width=2 for better layout
    
    # 3 Channel buttons
    buttons = [types.InlineKeyboardButton(text=f"Join {ch[1:]}", url=f"https://t.me/{ch[1:]}") for ch in CHANNELS]
    
    # Check Joined button
    check_button = types.InlineKeyboardButton(text="Check Joined ✅", callback_data="check_join")
    
    # Add buttons to keyboard
    for btn in buttons:
        keyboard.add(btn)
    keyboard.add(check_button)
    
    bot.send_message(
        message.chat.id,
        "I'm referral bot\nPlease join all channels below:",
        reply_markup=keyboard
    )

# Callback for Check Joined
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    joined_all = True
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch, call.from_user.id)
            if member.status not in ['member', 'administrator', 'creator']:
                joined_all = False
                break
        except:
            joined_all = False
            break
    
    if joined_all:
        bot.answer_callback_query(call.id, "✅ You joined all channels!")
    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined all channels.")

# Run bot
bot.polling()
