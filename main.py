# main.py - Inline-only Wallet + Marketplace (Option B) - replace your existing main.py with this

import os
import threading
import time
import uuid
import sqlite3
from flask import Flask
import telebot
from telebot import types

# ----------------- Configuration -----------------
BOT_TOKEN = os.environ.get("8320599781:AAFIJuOv5o1rwJD7Ayec8MrqKYXxpUoTCxw")
if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN in environment (Replit Secrets)")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

ADMIN_ID = 7257298716  # change if needed
DB_PATH = "bot_data.db"

# ---------- DB helpers ----------
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

# ---------- Basic data helpers ----------
def ensure_user(user):
    db_execute("INSERT OR IGNORE INTO users(user_id, username, balance) VALUES (?, ?, ?)",
               (user.id, getattr(user, "username", None), 0))

def get_balance(user_id):
    rows = db_execute("SELECT balance FROM users WHERE user_id = ?", (user_id,), fetch=True)
    return float(rows[0][0]) if rows else 0.0

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
    rows = db_execute("SELECT id, title, price, url FROM links WHERE id = ?", (link_id,), fetch=True)
    return rows[0] if rows else None

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
    bal = get_balance(user_id)
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(f"💼 Wallet", callback_data=f"wallet"),
        types.InlineKeyboardButton(f"📦 Market", callback_data=f"market"),
        types.InlineKeyboardButton(f"📜 Purchases", callback_data=f"purchases"),
        types.InlineKeyboardButton(f"➕ Add Funds", callback_data=f"addfunds"),
        types.InlineKeyboardButton(f"📖 Help", callback_data=f"help"),
    )
    if user_id == ADMIN_ID:
        kb.add(types.InlineKeyboardButton("🔧 Admin", callback_data="admin_panel"))
    return kb

def wallet_kb(user_id):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(f"Add ₹50", callback_data=f"add::50"),
        types.InlineKeyboardButton(f"Add ₹100", callback_data=f"add::100"),
        types.InlineKeyboardButton(f"Add ₹200", callback_data=f"add::200"),
        types.InlineKeyboardButton(f"Request Manual Top-up", callback_data=f"manual_topup"),
    )
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main"))
    return kb

def market_page_kb(link_id):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("Buy this link", callback_data=f"buy::{link_id}"))
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main"))
    return kb

def market_list_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    rows = list_links()
    if not rows:
        kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main"))
        return kb
    for r in rows:
        lid, title, price = r
        kb.add(types.InlineKeyboardButton(f"{title} — ₹{price:.2f}", callback_data=f"market_view::{lid}"))
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main"))
    return kb

def purchases_kb(user_id):
    kb = types.InlineKeyboardMarkup(row_width=1)
    rows = get_user_purchases(user_id)
    if not rows:
        kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main"))
        return kb
    for r in rows:
        lid, price, _ = r
        link = get_link(lid)
        title = link[1] if link else "Unknown"
        kb.add(types.InlineKeyboardButton(f"{title} — ₹{price:.2f}", callback_data="noop"))
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main"))
    return kb

def admin_panel_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("➕ Add Link", callback_data="admin_addlink"),
        types.InlineKeyboardButton("🗑️ Remove Link", callback_data="admin_removelink"),
    )
    kb.add(
        types.InlineKeyboardButton("💳 Pending Payments", callback_data="admin_pending"),
        types.InlineKeyboardButton("📦 All Links", callback_data="admin_listlinks"),
    )
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main"))
    return kb

def admin_pending_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    rows = get_pending_payments()
    if not rows:
        kb.add(types.InlineKeyboardButton("No pending payments", callback_data="noop"))
        kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="admin_panel"))
        return kb
    for r in rows:
        pid, uid, amount, _ = r
        kb.add(types.InlineKeyboardButton(f"{pid[:8]} — ₹{amount:.2f} by {uid}", callback_data=f"admin_confirm::{pid}"))
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="admin_panel"))
    return kb

def admin_listlinks_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    rows = list_links()
    if not rows:
        kb.add(types.InlineKeyboardButton("No links", callback_data="noop"))
        kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="admin_panel"))
        return kb
    for r in rows:
        lid, title, price = r
        kb.add(types.InlineKeyboardButton(f"{title} — ₹{price:.2f}", callback_data=f"admin_viewlink::{lid}"))
    kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="admin_panel"))
    return kb

# ---------- Message text builders ----------
def main_menu_text(user_id):
    bal = get_balance(user_id)
    purchases = db_execute("SELECT COUNT(*) FROM purchases WHERE user_id = ?", (user_id,), fetch=True)[0][0]
    return f"🌟 Welcome!\nBalance: ₹{bal:.2f}\nPurchases: {purchases}\n\nChoose an action:"

# ---------- Start (entry) ----------
@bot.message_handler(commands=['start'])
def cmd_start_inline(message):
    ensure_user(message.from_user)
    kb = main_menu_kb(message.from_user.id)
    bot.send_message(message.chat.id, main_menu_text(message.from_user.id), reply_markup=kb)

# ---------- Central callback handler ----------
@bot.callback_query_handler(func=lambda c: True)
def inline_router(call):
    data = call.data
    uid = call.from_user.id
    ensure_user(call.from_user)

    # --- navigation ---
    if data == "back_to_main":
        bot.edit_message_text(main_menu_text(uid), chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=main_menu_kb(uid))
        bot.answer_callback_query(call.id)
        return

    if data == "wallet":
        bal = get_balance(uid)
        txt = f"💼 Wallet\nBalance: ₹{bal:.2f}\n\nChoose top-up amount:"
        bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=wallet_kb(uid))
        bot.answer_callback_query(call.id)
        return

    if data.startswith("add::"):
        amt = float(data.split("::",1)[1])
        payid = create_payment(uid, amt)
        txt = f"🧾 Invoice created: `{payid}`\nAmount: ₹{amt:.2f}\n\nTo complete (simulated): ask admin to confirm this invoice in admin panel."
        bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main")))
        bot.answer_callback_query(call.id, "Invoice created. Ask admin to confirm.")
        return

    if data == "manual_topup":
        txt = "Manual top-up request created. Please contact admin with payment proof and invoice id will be approved there."
        bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main")))
        bot.answer_callback_query(call.id)
        return

    if data == "market":
        rows = list_links()
        if not rows:
            bot.edit_message_text("No links available right now. ◀️ Back", chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main")))
            bot.answer_callback_query(call.id)
            return
        bot.edit_message_text("📦 Market - choose an item:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=market_list_kb())
        bot.answer_callback_query(call.id)
        return

    if data.startswith("market_view::"):
        lid = data.split("::",1)[1]
        link = get_link(lid)
        if not link:
            bot.answer_callback_query(call.id, "Link not found.")
            return
        _, title, price, url = link
        txt = f"📎 {title}\nPrice: ₹{float(price):.2f}"
        bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=market_page_kb(lid))
        bot.answer_callback_query(call.id)
        return

    if data.startswith("buy::"):
        lid = data.split("::",1)[1]
        link = get_link(lid)
        if not link:
            bot.answer_callback_query(call.id, "Link not found.")
            return
        _, title, price, url = link
        price = float(price)
        bal = get_balance(uid)
        if bal < price:
            bot.answer_callback_query(call.id, "Insufficient balance. Use Add Funds.", show_alert=True)
            return
        adjust_balance(uid, -price)
        record_purchase(uid, lid, price)
        txt = f"✅ Purchased: {title}\nHere is your link:\n{url}\n\nRemaining balance: ₹{get_balance(uid):.2f}"
        bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main")))
        bot.answer_callback_query(call.id, "Purchase complete")
        return

    if data == "purchases":
        rows = get_user_purchases(uid)
        if not rows:
            bot.edit_message_text("You have no purchases yet.", chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main")))
            bot.answer_callback_query(call.id)
            return
        text = "📜 Your purchases:\n"
        for r in rows:
            lid, price, ts = r
            link = get_link(lid)
            title = link[1] if link else "Unknown"
            text += f"- {title} | ₹{price:.2f}\n"
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=purchases_kb(uid))
        bot.answer_callback_query(call.id)
        return

    if data == "help":
        txt = ("Help:\n• Use Wallet → Add Funds to top up (preset amounts).\n"
               "• Market → browse and buy links.\n• Admin users can confirm payments.")
        bot.edit_message_text(txt, chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main")))
        bot.answer_callback_query(call.id)
        return

    # ---------- Admin routes ----------
    if data == "admin_panel":
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.", show_alert=True)
            return
        bot.edit_message_text("🔧 Admin Panel", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=admin_panel_kb())
        bot.answer_callback_query(call.id)
        return

    if data == "admin_pending":
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.", show_alert=True)
            return
        bot.edit_message_text("💳 Pending Payments", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=admin_pending_kb())
        bot.answer_callback_query(call.id)
        return

    if data.startswith("admin_confirm::"):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.", show_alert=True)
            return
        pid = data.split("::",1)[1]
        pay = db_execute("SELECT id, user_id, amount, status FROM payments WHERE id = ?", (pid,), fetch=True)
        if not pay:
            bot.answer_callback_query(call.id, "Payment not found.", show_alert=True)
            return
        pid, user_id, amount, status = pay[0]
        if status == "paid":
            bot.answer_callback_query(call.id, "Already paid.")
            return
        set_payment_status(pid, "paid")
        adjust_balance(user_id, float(amount))
        bot.answer_callback_query(call.id, "Payment confirmed and user credited.")
        bot.edit_message_text("💳 Pending Payments", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=admin_pending_kb())
        bot.send_message(user_id, f"✅ Your top-up of ₹{float(amount):.2f} has been approved by admin. Current balance: ₹{get_balance(user_id):.2f}")
        return

    if data == "admin_addlink":
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.")
            return
        bot.edit_message_text("Send new link details as: title | price | url\nExample:\nNaruto Ep1 | 50 | https://example.com/ep1",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Back", callback_data="admin_panel")))
        bot.answer_callback_query(call.id)
        @bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID)
        def _collect_new_link(msg):
            if '|' not in msg.text:
                bot.reply_to(msg, "Invalid format. Use: title | price | url")
                return
            try:
                title, price, url = [x.strip() for x in msg.text.split("|", 2)]
                price = float(price)
            except Exception as e:
                bot.reply_to(msg, "Error parsing. Ensure price is numeric.")
                return
            lid = add_link(title, price, url, seller=ADMIN_ID)
            bot.reply_to(msg, f"Link added: {title} | ₹{price:.2f}\nID: {lid}")
        return

    if data == "admin_listlinks":
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.")
            return
        bot.edit_message_text("📦 All Links", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=admin_listlinks_kb())
        bot.answer_callback_query(call.id)
        return

    if data.startswith("admin_viewlink::"):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.")
            return
        lid = data.split("::",1)[1]
        link = get_link(lid)
        if not link:
            bot.answer_callback_query(call.id, "Not found.")
            return
        _, title, price, url = link
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Remove", callback_data=f"admin_remove::{lid}"))
        kb.add(types.InlineKeyboardButton("◀️ Back", callback_data="admin_listlinks"))
        bot.edit_message_text(f"{title}\n₹{price:.2f}\n{url}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("admin_remove::"):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Not allowed.")
            return
        lid = data.split("::",1)[1]
        db_execute("DELETE FROM links WHERE id = ?", (lid,))
        bot.answer_callback_query(call.id, "Removed.")
        bot.edit_message_text("📦 All Links", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=admin_listlinks_kb())
        return

    # noop / unknown
    bot.answer_callback_query(call.id, "Action not supported.")

# ---------- Flask keepalive endpoint ----------
@app.route("/")
def index():
    return "Bot is running ✅"

# ---------- Bot runner (polling in background) ----------
def run_bot_polling():
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=90)
        except Exception as e:
            print("Polling error:", e)
            time.sleep(5)

if __name__ == "__main__":
    t = threading.Thread(target=run_bot_polling, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
