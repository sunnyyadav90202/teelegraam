import os
import threading
from flask import Flask
import telebot

BOT_TOKEN = os.environ.get("8320599781:AAFIJuOv5o1rwJD7Ayec8MrqKYXxpUoTCxw")
if not BOT_TOKEN:
    raise RuntimeError("Set the BOT_TOKEN environment variable in Replit Secrets")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# ---- Telegram handlers ----
@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.reply_to(message, "Hi! I'm your bot. Send me anything and I'll echo it back.")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.reply_to(message, "Commands:\n/start - welcome\n/help - this message\n/echo <text> - bot will reply with <text>")

@bot.message_handler(commands=['echo'])
def cmd_echo(message):
    text = message.text.partition(' ')[2]
    if text:
        bot.reply_to(message, text)
    else:
        bot.reply_to(message, "Usage: /echo hello")

@bot.message_handler(func=lambda m: True)
def echo_all(message):
    # simple echo; replace with your bot logic
    bot.reply_to(message, f"You said: {message.text}")

def run_bot_polling():
    # infinity_polling automatically reconnects on errors
    bot.infinity_polling(timeout=20, long_polling_timeout = 90)

# ---- Keepalive endpoint for uptime monitor ----
@app.route('/ping')
def ping():
    return "pong", 200

if __name__ == '__main__':
    # start bot in background thread
    t = threading.Thread(target=run_bot_polling, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 3000))
    # Run Flask (this keeps the HTTP server running for pings)
    app.run(host="0.0.0.0", port=port)
