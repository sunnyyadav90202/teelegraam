import os
import requests
from pyrogram import Client, filters
from flask import Flask
from threading import Thread

API_ID = int(os.getenv("21629245"))
API_HASH = os.getenv("21678b79dd7741264131705ca6563e59")
BOT_TOKEN = os.getenv("8117972904:AAHRSvFFeOlf17_LExSYRLSGHKunkV8elXA")

bot = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

TERA_API = "https://teradlrobot.cheemsbackup.workers.dev/?url="

@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text(
        "Send me a Terabox link.\n\n⚠️ Free bot – limited size & speed."
    )

@bot.on_message(filters.text & ~filters.command)
async def download(_, message):
    url = message.text.strip()

    if "tera" not in url:
        return await message.reply_text("❌ Invalid Terabox link.")

    msg = await message.reply_text("🔍 Fetching file...")

    try:
        r = requests.get(TERA_API + url, timeout=30)
        r.raise_for_status()
    except Exception:
        return await msg.edit("❌ Failed to fetch download link.")

    file_path = "download.bin"
    with open(file_path, "wb") as f:
        f.write(r.content)

    await msg.edit("📤 Uploading to Telegram...")

    await message.reply_document(file_path)
    os.remove(file_path)
    await msg.delete()

# Flask keep-alive
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

Thread(target=run_flask).start()

bot.run()
