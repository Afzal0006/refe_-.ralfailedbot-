import logging
import asyncio
from urllib.parse import urlencode

import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from pymongo import MongoClient

# ========= CONFIG =========
BOT_TOKEN = "8357734886:AAHQi1zmj9q8B__7J-2dyYUWVTQrMRr65Dc"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"   # e.g. "mongodb+srv://user:pass@cluster0.mongodb.net"
DB_NAME = "tempmailbot"
# ==========================

API_BASE = "https://www.1secmail.com/api/v1/"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----- Mongo Setup -----
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
users_col = db["users"]  # stores {"_id": user_id, "login":..., "domain":..., "address":...}


# -------- Helpers -----------
async def gen_random_mail(session: aiohttp.ClientSession):
    params = {"action": "genRandomMailbox", "count": 1}
    url = API_BASE + "?" + urlencode(params)
    async with session.get(url) as r:
        data = await r.json()
        addr = data[0]
        login, domain = addr.split("@")
        return {"login": login, "domain": domain, "address": addr}


async def get_messages(session: aiohttp.ClientSession, login: str, domain: str):
    params = {"action": "getMessages", "login": login, "domain": domain}
    url = API_BASE + "?" + urlencode(params)
    async with session.get(url) as r:
        return await r.json()


async def read_message(session: aiohttp.ClientSession, login: str, domain: str, msg_id: int):
    params = {"action": "readMessage", "login": login, "domain": domain, "id": msg_id}
    url = API_BASE + "?" + urlencode(params)
    async with session.get(url) as r:
        return await r.json()


# -------- Bot Handlers --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Welcome to *Temp Mail Bot!*\n\n"
        "Commands:\n"
        "/new - Generate new temporary email\n"
        "/address - Show current email\n"
        "/inbox - Show inbox\n"
        "/delete - Clear current session"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def new_mail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with aiohttp.ClientSession() as s:
        try:
            info = await gen_random_mail(s)
        except:
            await update.message.reply_text("❌ Could not generate mailbox. Try again.")
            return

    users_col.update_one(
        {"_id": user_id},
        {"$set": {"login": info["login"], "domain": info["domain"], "address": info["address"]}},
        upsert=True,
    )
    await update.message.reply_text(f"✅ New Temp Email:\n`{info['address']}`", parse_mode="Markdown")


async def show_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = users_col.find_one({"_id": user_id})
    if not user:
        await update.message.reply_text("❌ No email found. Use /new to generate.")
        return
    await update.message.reply_text(f"📧 Your Email:\n`{user['address']}`", parse_mode="Markdown")


async def inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = users_col.find_one({"_id": user_id})
    if not user:
        await update.message.reply_text("❌ No session. Use /new first.")
        return

    async with aiohttp.ClientSession() as s:
        try:
            msgs = await get_messages(s, user["login"], user["domain"])
        except:
            await update.message.reply_text("⚠️ Failed to fetch inbox.")
            return

    if not msgs:
        await update.message.reply_text("📭 Inbox empty.")
        return

    lines, buttons = [], []
    for m in msgs:
        mid = m["id"]
        subj = m.get("subject", "(no subject)")
        frm = m.get("from", "")
        lines.append(f"*{mid}* — `{subj}`\nFrom: {frm}")
        buttons.append([InlineKeyboardButton(f"Read {mid}", callback_data=f"read:{mid}")])

    await update.message.reply_text(
        "📩 Inbox:\n\n" + "\n\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    user_id = q.from_user.id

    if data.startswith("read:"):
        msg_id = int(data.split(":")[1])
        user = users_col.find_one({"_id": user_id})
        if not user:
            await q.edit_message_text("❌ No session found. Use /new first.")
            return

        async with aiohttp.ClientSession() as s:
            try:
                msg = await read_message(s, user["login"], user["domain"], msg_id)
            except:
                await q.edit_message_text("⚠️ Failed to read message.")
                return

        body = msg.get("textBody") or msg.get("body") or "(empty)"
        if len(body) > 3500:
            body = body[:3500] + "\n\n[Truncated]"

        text = f"*Subject:* {msg.get('subject')}\n*From:* {msg.get('from')}\n\n{body}"
        await q.edit_message_text(text, parse_mode="Markdown")


async def delete_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    res = users_col.delete_one({"_id": user_id})
    if res.deleted_count > 0:
        await update.message.reply_text("🗑️ Session deleted.")
    else:
        await update.message.reply_text("⚠️ No session found.")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_mail))
    app.add_handler(CommandHandler("address", show_address))
    app.add_handler(CommandHandler("inbox", inbox))
    app.add_handler(CommandHandler("delete", delete_session))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
