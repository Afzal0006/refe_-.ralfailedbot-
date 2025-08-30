from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from pymongo import MongoClient
import openai
from dotenv import load_dotenv
import os

# ===== LOAD ENV VARIABLES =====
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# ===== INIT =====
openai.api_key = OPENAI_API_KEY
client = MongoClient(MONGO_URI)
db = client["ai_bot_db"]
messages_collection = db["messages"]

# ===== /start COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your AI Bot. I remember our conversation. Send me a message!")

# ===== MESSAGE HANDLER =====
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text

    # Store user message
    messages_collection.insert_one({
        "user_id": user_id,
        "message": user_text,
        "from_bot": False
    })

    # Retrieve last 5 messages from this user for context
    history = messages_collection.find({"user_id": user_id}).sort("_id", -1).limit(5)
    prompt_text = ""
    for msg in reversed(list(history)):
        if msg.get("from_bot"):
            prompt_text += f"AI: {msg['message']}\n"
        else:
            prompt_text += f"User: {msg['message']}\n"
    prompt_text += "AI:"

    # Get AI response
    try:
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt_text,
            max_tokens=150
        )
        reply = response.choices[0].text.strip()
    except Exception as e:
        reply = f"Error: {str(e)}"

    # Store AI reply
    messages_collection.insert_one({
        "user_id": user_id,
        "message": reply,
        "from_bot": True
    })

    # Send reply
    await update.message.reply_text(reply)

# ===== MAIN =====
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

print("Bot is running...")
app.run_polling()
