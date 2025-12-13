import telebot
import sqlite3
from telebot import types

# ========== CONFIG ==========
BOT_TOKEN = "8117972904:AAHRSvFFeOlf17_LExSYRLSGHKunkV8elXA"
CHANNEL_USERNAME = "https://t.me/earning_mafia_007"  # without https://
ADMIN_ID = 123456789
# ============================

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ---------- DATABASE ----------
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    ref_by INTEGER,
    referrals INTEGER DEFAULT 0
)
""")
conn.commit()

# ---------- FORCE JOIN CHECK ----------
def is_joined(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ["member", "administrator", "creator"]
    except:
        return False

# ---------- START COMMAND ----------
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    args = message.text.split()

    if not is_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "Join Channel",
                url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "✅ Joined",
                callback_data="check_join"
            )
        )
        bot.send_message(
            message.chat.id,
            "🚫 <b>You must join our channel to use this bot.</b>",
            reply_markup=markup
        )
        return

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    user_exists = cursor.fetchone()

    if not user_exists:
        ref_by = None
        if len(args) > 1 and args[1].isdigit():
            ref_by = int(args[1])
            cursor.execute(
                "UPDATE users SET referrals = referrals + 1 WHERE user_id=?",
                (ref_by,)
            )

        cursor.execute(
            "INSERT INTO users (user_id, ref_by) VALUES (?, ?)",
            (user_id, ref_by)
        )
        conn.commit()

    ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"

    bot.send_message(
        message.chat.id,
        f"""
✅ <b>Welcome!</b>

👥 <b>Your Referral Link:</b>
<code>{ref_link}</code>

📊 Use /stats to check your referrals
"""
    )

# ---------- CALLBACK JOIN CHECK ----------
@bot.callback_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    if is_joined(call.from_user.id):
        bot.answer_callback_query(call.id, "Verified!")
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "You haven't joined yet!", show_alert=True)

# ---------- STATS ----------
@bot.message_handler(commands=["stats"])
def stats(message):
    cursor.execute(
        "SELECT referrals FROM users WHERE user_id=?",
        (message.from_user.id,)
    )
    data = cursor.fetchone()
    referrals = data[0] if data else 0

    bot.send_message(
        message.chat.id,
        f"📈 <b>Your Total Referrals:</b> {referrals}"
    )

# ---------- RUN ----------
bot.infinity_polling()
