from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from pymongo import MongoClient
import logging

# ===== Config =====
BOT_TOKEN = "8357734886:AAHQi1zmj9q8B__7J-2dyYUWVTQrMRr65Dc"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Channels
CHANNELS = [
    ("Store", "https://t.me/testing7889gy"),
    ("Point", "https://t.me/SexyEmoji"),
    ("Loda", "https://t.me/guiii8889")
]

# ===== MongoDB =====
client = MongoClient(MONGO_URI)
db = client["startbot"]
users = db["users"]

# ===== Logging =====
logging.basicConfig(level=logging.INFO)

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name

    # Save user in DB
    users.update_one(
        {"user_id": user.id},
        {"$set": {"user_id": user.id, "name": name}},
        upsert=True
    )

    keyboard = [[InlineKeyboardButton(text, url=url)] for text, url in CHANNELS]
    keyboard.append([InlineKeyboardButton("✅ Joined", callback_data="check")])

    await update.message.reply_photo(
        photo="https://i.ibb.co/FbVHf8JG/x.jpg",
        caption=f"Hlo {name}\nJoin channel for free",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== Check Button =====
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    ok = True

    for _, url in CHANNELS:
        chat_id = url.split("/")[-1]  # channel username extract
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status in ["left", "kicked"]:
                ok = False
        except:
            ok = False

    if ok:
        # update user status in DB
        users.update_one({"user_id": user_id}, {"$set": {"joined": True}})

        # Purana msg delete
        await query.message.delete()
        await query.message.reply_text("Hlo sir how r u")
    else:
        await query.message.reply_text("⚠️ Please join all channels first!")

# ===== Main =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check"))
    app.run_polling()

if __name__ == "__main__":
    main()
