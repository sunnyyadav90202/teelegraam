# main.py - Clean inline-only wallet + marketplace bot
# Replace your existing main.py with this file.

import os
import threading
import time
import uuid
import sqlite3
from flask import Flask
import telebot
from telebot import types

# ---------- Config ----------
BOT_TOKEN = os.environ.get("8320599781:AAFIJuOv5o1rwJD7Ayec8MrqKYXxpUoTCxw")
if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN in Replit Secrets")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

ADMIN_ID = 7257298716   # change to your telegram id if different
DB_PATH = "bot_data.db"

# ---------- Database helpers ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance REAL DEFAULT 0
                   )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS links (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    price REAL,
                    url TEXT,
                    seller INTEGER,
                    created_at INTEGER
                   )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS purchases (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    link_id TEXT,
                    price REAL,
                    created_at INTEGER
                   )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS payments (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    amount REAL,
                    status TEXT,
                    created_at INTEGER
                   )""")
    conn.commit()
    conn.close()

def db_execute(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    data = None
    if fetch:
        data = cur.fetchall()
    conn.commit()
    conn.close()
    return data

init_db()

# ---------- helpers ----------
def ensure_user(user):
    db_execute("INSERT OR IGNORE INTO users(user_id, username, balance) VALUES (?, ?, ?)",
               (user.id, getattr(user, "username", None), 0))

def get_balance(user_id):
    r = db_execute("SELECT balance FROM users WHERE user_id = ?", (user_id,), fetch=True)
    return float(r[0][0]) if r else 0.0

def adjust_balance(user_id, delta):
    db_execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (delta, user_id))

def add_link(title, price, url, seller=ADMIN_ID):
    lid = str(uuid.uuid4())
    db_execute("INSERT INTO links(id, title, price, url, seller, created_at) VALUES (?, ?, ?, ?, ?, ?)",
               (lid, title, price, url, seller, int(time.time())))
    return lid

def list_links():
    return db_execute("SELECT id, title, price FROM links ORDER BY created_at DESC", fetch=True)

def get_link(link_id):
    r = db_execute("SELECT id, title, price, url FROM links WHERE id = ?", (link_id,), fetch=True)
    return r[0] if r else None

def record_purchase(user_id, link_id, price):
    pid = str(uuid.uuid4())
    db_execute("INSERT INTO purchases(id, user_id, link_id, price, created_at) VALUES (?, ?, ?, ?, ?)",
               (pid, user_id, link_id, price, int(time.time())))
    return pid

def create_payment(user_id, amount):
    payid = str(uuid.uuid4())
    db_execute("INSERT INTO payments(id, user_id, amount, status, created_at) VALUES (?, ?, ?, ?, ?)",
               (payid, user_id, amount, "pending", int(time.time())))
    return payid

def get_pending_payments():
    return db_execute("SELECT id, user_id, amount, created_at FROM payments WHERE status = 'pending' ORDER BY created_at", fetch=True)

def set_payment_status(payment_id, status):
    db_execute("UPDATE payments SET status = ? WHERE id = ?", (status, payment_id))

def get_user_purchases(user_id):
    return db_execute("SELECT link_id, price, created_at FROM purchases WHERE user_id = ? ORDER BY created_at DESC", (user_id,), fetch=True)

# ---------- UI builders ----------
def main_menu_kb(user_id):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("💼 Wallet", callback_data="wallet"),
        types.InlineKeyboardButton("📦 Market", callback_data="market"),
        types.InlineKeyboardButton("📜 Purchases", callback_data="purchases"),
        types.InlineKeyboardButton("➕ Add Funds", callback_data="addfunds"),
        types.InlineKeyboardButton("📖 Help", callback_data="help")
    )
    if user_id == ADMIN_ID:
        kb.add(types.InlineKeyboardButton("🔧 Admin", callback_data="admin_panel"))
    return kb

def wallet_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("Add ₹50", callback_data="add::50"),
        types.InlineKeyboardButton("Add ₹100", callback_data="add::100"),
        types.InlineKeyboardButton("Add ₹200", callback_data="add::200"),
        types.InlineKeyboardButton("Request Manual Top-up", callback_data="manual_topup")
    )
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="back"))
    return kb

def market_list_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    rows = list_links()
    if not rows:
        kb.add(types.InlineKeyboardButton("No items — Back", callback_data="back"))
        return kb
    for lid, title, price in rows:
        kb.add(types.InlineKeyboardButton(f"{title} — ₹{price:.2f}", callback_data=f"view::{lid}"))
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="back"))
    return kb

def market_item_kb(lid):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("Buy", callback_data=f"buy::{lid}"))
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="market"))
    return kb

def purchases_kb(user_id):
    kb = types.InlineKeyboardMarkup(row_width=1)
    rows = get_user_purchases(user_id)
    if not rows:
        kb.add(types.InlineKeyboardButton("No purchases — Back", callback_data="back"))
        return kb
    for lid, price, _ in rows:
        link = get_link(lid)
        title = link[1] if link else "Unknown"
        kb.add(types.InlineKeyboardButton(f"{title} — ₹{price:.2f}", callback_data="noop"))
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="back"))
    return kb

def admin_panel_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("➕ Add Link", callback_data="admin_add"),
        types.InlineKeyboardButton("💳 Pending Payments", callback_data="admin_pending"),
        types.InlineKeyboardButton("📦 All Links", callback_data="admin_links"),
    )
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="back"))
    return kb

def admin_pending_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    rows = get_pending_payments()
    if not rows:
        kb.add(types.InlineKeyboardButton("No pending", callback_data="noop"))
        kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="admin_panel"))
        return kb
    for pid, uid, amt, _ in rows:
        kb.add(types.InlineKeyboardButton(f"{pid[:8]} — ₹{amt:.2f} by {uid}", callback_data=f"confirm::{pid}"))
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="admin_panel"))
    return kb

def admin_links_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    rows = list_links()
    if not rows:
        kb.add(types.InlineKeyboardButton("No links", callback_data="noop"))
        kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="admin_panel"))
        return kb
    for lid, title, price in rows:
        kb.add(types.InlineKeyboardButton(f"{title} — ₹{price:.2f}", callback_data=f"alview::{lid}"))
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="admin_panel"))
    return kb

# ---------- Text builders ----------
def main_text(user_id):
    bal = get_balance(user_id)
    cnt = db_execute("SELECT COUNT(*) FROM purchases WHERE user_id = ?", (user_id,), fetch=True)[0][0]
    return f"🌟 Welcome!\nBalance: ₹{bal:.2f}\nPurchases: {cnt}\n\nChoose an action:"

# ---------- Handlers ----------
@bot.message_handler(commands=['start'])
def start_cmd(m):
    ensure_user(m.from_user)
    bot.send_message(m.chat.id, main_text(m.from_user.id), reply_markup=main_menu_kb(m.from_user.id))

@bot.callback_query_handler(func=lambda c: True)
def router(call):
    data = call.data or ""
    uid = call.from_user.id
    ensure_user(call.from_user)

    if data == "back":
        bot.edit_message_text(main_text(uid), chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=main_menu_kb(uid))
        bot.answer_callback_query(call.id); return

    if data == "wallet":
        bot.edit_message_text(f"💼 Wallet\nBalance: ₹{get_balance(uid):.2f}\n\nChoose top-up:", chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=wallet_kb()); bot.answer_callback_query(call.id); return

    if data.startswith("add::"):
        amt = float(data.split("::",1)[1])
        pid = create_payment(uid, amt)
        bot.edit_message_text(f"🧾 Invoice: `{pid}`\nAmount: ₹{amt:.2f}\nAsk admin to confirm.", chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="back")))
        bot.answer_callback_query(call.id, "Invoice created"); return

    if data == "addfunds" or data == "manual_topup":
        bot.edit_message_text("Use Wallet → choose an amount to create invoice (admin will confirm).", chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="back")))
        bot.answer_callback_query(call.id); return

    if data == "market":
        rows = list_links()
        if not rows:
            bot.edit_message_text("No items available.", chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="back")))
            bot.answer_callback_query(call.id); return
        bot.edit_message_text("📦 Market — choose an item:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=market_list_kb()); bot.answer_callback_query(call.id); return

    if data.startswith("view::"):
        lid = data.split("::",1)[1]
        link = get_link(lid)
        if not link:
            bot.answer_callback_query(call.id, "Not found."); return
        _, title, price, url = link
        bot.edit_message_text(f"📎 {title}\nPrice: ₹{float(price):.2f}", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=market_item_kb(lid)); bot.answer_callback_query(call.id); return

    if data.startswith("buy::"):
        lid = data.split("::",1)[1]
        link = get_link(lid)
        if not link:
            bot.answer_callback_query(call.id, "Not found."); return
        _, title, price, url = link
        price = float(price)
        if get_balance(uid) < price:
            bot.answer_callback_query(call.id, "Insufficient balance.", show_alert=True); return
        adjust_balance(uid, -price)
        record_purchase(uid, lid, price)
        bot.edit_message_text(f"✅ Purchased: {title}\nLink:\n{url}\n\nRemaining: ₹{get_balance(uid):.2f}", chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="back")))
        bot.answer_callback_query(call.id, "Purchase successful"); return

    if data == "purchases":
        rows = get_user_purchases(uid)
        if not rows:
            bot.edit_message_text("You have no purchases.", chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="back")))
            bot.answer_callback_query(call.id); return
        text = "📜 Your purchases:\n" + "\n".join([f"- {get_link(r[0])[1]} | ₹{r[1]:.2f}" for r in rows])
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=purchases_kb(uid))
        bot.answer_callback_query(call.id); return

    if data == "help":
        bot.edit_message_text("Help:\nUse Wallet → Add Funds → Admin confirm.\nMarket → buy items.", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="back")))
        bot.answer_callback_query(call.id); return

    # Admin-only
    if data == "admin_panel":
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.", show_alert=True); return
        bot.edit_message_text("🔧 Admin Panel", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_panel_kb())
        bot.answer_callback_query(call.id); return

    if data == "admin_pending":
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.", show_alert=True); return
        bot.edit_message_text("💳 Pending payments", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_pending_kb())
        bot.answer_callback_query(call.id); return

    if data.startswith("confirm::"):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.", show_alert=True); return
        pid = data.split("::",1)[1]
        row = db_execute("SELECT id, user_id, amount, status FROM payments WHERE id = ?", (pid,), fetch=True)
        if not row:
            bot.answer_callback_query(call.id, "Not found."); return
        pid, user_id, amount, status = row[0]
        if status == "paid":
            bot.answer_callback_query(call.id, "Already paid."); return
        set_payment_status(pid, "paid"); adjust_balance(user_id, float(amount))
        bot.answer_callback_query(call.id, "Payment confirmed.")
        bot.edit_message_text("💳 Pending payments", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_pending_kb())
        bot.send_message(user_id, f"✅ Your top-up of ₹{float(amount):.2f} is approved. New balance: ₹{get_balance(user_id):.2f}")
        return

    if data == "admin_add":
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.", show_alert=True); return
        bot.edit_message_text("Send a message to me with format: title | price | url", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="admin_panel")))
        bot.answer_callback_query(call.id); return

    if data == "admin_links":
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.", show_alert=True); return
        bot.edit_message_text("📦 All links", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_links_kb())
        bot.answer_callback_query(call.id); return

    if data.startswith("alview::"):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.", show_alert=True); return
        lid = data.split("::",1)[1]
        link = get_link(lid)
        if not link:
            bot.answer_callback_query(call.id, "Not found."); return
        _, title, price, url = link
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Remove", callback_data=f"arem::{lid}"))
        kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="admin_links"))
        bot.edit_message_text(f"{title}\n₹{price:.2f}\n{url}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id); return

    if data.startswith("arem::"):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.", show_alert=True); return
        lid = data.split("::",1)[1]
        db_execute("DELETE FROM links WHERE id = ?", (lid,))
        bot.answer_callback_query(call.id, "Removed.")
        bot.edit_message_text("📦 All links", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_links_kb())
        return

    # fallback
    bot.answer_callback_query(call.id, "Action not supported.")

# ---------- Admin text handler to add links (admin types one message) ----------
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and '|' in m.text)
def admin_create_link(msg):
    try:
        title, price, url = [x.strip() for x in msg.text.split("|", 2)]
        price = float(price)
    except:
        bot.reply_to(msg, "Invalid format. Use: title | price | url")
        return
    lid = add_link(title, price, url, seller=ADMIN_ID)
    bot.reply_to(msg, f"Link added: {title} | ₹{price:.2f}\nID: {lid}")

# ---------- Flask keepalive ----------
@app.route("/")
def home():
    return "Bot running"

# ---------- Bot runner ----------
def run_polling():
    while True:
        try:
            print(">>> Polling started")
            bot.infinity_polling(timeout=60, long_polling_timeout=90)
        except Exception as e:
            print("Polling error:", e)
            time.sleep(3)

if __name__ == "__main__":
    t = threading.Thread(target=run_polling, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
