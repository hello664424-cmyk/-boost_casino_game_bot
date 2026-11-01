import os
import sqlite3
import random
import logging
import telebot
from telebot import types

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch variables from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Optional channel handle for join-to-play feature (e.g., @YourChannel)
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "") 

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Database Initialization
DB_NAME = "casino_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 100.0,
            referred_by INTEGER,
            referrals_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_user(user_id, username=None, referrer_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, balance, referrals_count FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        # Create new user
        cursor.execute(
            "INSERT INTO users (user_id, username, balance, referred_by) VALUES (?, ?, ?, ?)",
            (user_id, username, 100.0, referrer_id)
        )
        # Handle referral bonus
        if referrer_id and referrer_id != user_id:
            cursor.execute("UPDATE users SET balance = balance + 25.0, referrals_count = referrals_count + 1 WHERE user_id = ?", (referrer_id,))
        conn.commit()
        cursor.execute("SELECT user_id, balance, referrals_count FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

    conn.close()
    return user

def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def build_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_slots = types.KeyboardButton("🎰 Play Slots ($10)")
    btn_dice = types.KeyboardButton("🎲 Roll Dice ($10)")
    btn_wheel = types.KeyboardButton("🎡 Spin Wheel ($20)")
    btn_profile = types.KeyboardButton("👤 Profile & Referrals")
    btn_boost = types.KeyboardButton("🚀 Free Bonus")
    markup.add(btn_slots, btn_dice, btn_wheel, btn_profile, btn_boost)
    return markup

@bot.message_handler(commands=["start"])
def cmd_start(message):
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])

    user = get_user(message.from_user.id, message.from_user.username, referrer_id)
    
    welcome_text = (
        f"<b>Welcome to the Telegram Casino Bot, {message.from_user.first_name}!</b> 🎰\n\n"
        f"💰 <b>Starting Balance:</b> ${user[1]:.2f}\n"
        f"Use the menu below to place bets, invite friends, or claim free rewards."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=build_main_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "👤 Profile & Referrals")
def show_profile(message):
    user = get_user(message.from_user.id, message.from_user.username)
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start={message.from_user.id}"

    text = (
        f"👤 <b>User Profile</b>\n"
        f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
        f"💵 <b>Balance:</b> ${user[1]:.2f}\n"
        f"👥 <b>Referrals:</b> {user[2]}\n\n"
        f"🔗 <b>Your Referral Link:</b>\n<code>{ref_link}</code>\n"
        f"<i>Share your link! Get +$25.00 for every invited friend.</i>"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda msg: msg.text == "🚀 Free Bonus")
def claim_bonus(message):
    user_id = message.from_user.id
    update_balance(user_id, 10.0)
    bot.send_message(message.chat.id, "🎁 You claimed your daily bonus of <b>+$10.00</b>!")

@bot.message_handler(func=lambda msg: msg.text == "🎰 Play Slots ($10)")
def play_slots(message):
    user_id = message.from_user.id
    user = get_user(user_id, message.from_user.username)
    bet = 10.0

    if user[1] < bet:
        bot.send_message(message.chat.id, "❌ Insufficient balance! Invite friends to earn more.")
        return

    update_balance(user_id, -bet)
    msg = bot.send_dice(message.chat.id, emoji="🎰")
    val = msg.dice.value

    # Native telegram slots payout calculation
    if val in [1, 22, 43]:  # 3 of a kind matching combination
        win = 100.0
        update_balance(user_id, win)
        bot.send_message(message.chat.id, f"🎉 <b>JACKPOT!</b> You won <b>+${win:.2f}</b>!")
    elif val in [16, 32, 48, 64]:  # 777
        win = 250.0
        update_balance(user_id, win)
        bot.send_message(message.chat.id, f"🔥 <b>SUPER JACKPOT 777!</b> You won <b>+${win:.2f}</b>!")
    else:
        bot.send_message(message.chat.id, "❌ You lost your bet. Try again!")

@bot.message_handler(func=lambda msg: msg.text == "🎲 Roll Dice ($10)")
def play_dice(message):
    user_id = message.from_user.id
    user = get_user(user_id, message.from_user.username)
    bet = 10.0

    if user[1] < bet:
        bot.send_message(message.chat.id, "❌ Insufficient balance!")
        return

    update_balance(user_id, -bet)
    msg = bot.send_dice(message.chat.id, emoji="🎲")
    val = msg.dice.value

    if val >= 4:
        win = bet * 1.5
        update_balance(user_id, win)
        bot.send_message(message.chat.id, f"🎲 Rolled a {val}! You won <b>+${win:.2f}</b>!")
    else:
        bot.send_message(message.chat.id, f"🎲 Rolled a {val}! Better luck next time.")

@bot.message_handler(func=lambda msg: msg.text == "🎡 Spin Wheel ($20)")
def spin_wheel(message):
    user_id = message.from_user.id
    user = get_user(user_id, message.from_user.username)
    bet = 20.0

    if user[1] < bet:
        bot.send_message(message.chat.id, "❌ Insufficient balance!")
        return

    update_balance(user_id, -bet)
    multipliers = [0, 0.5, 1.0, 1.5, 2.0, 5.0]
    result_mult = random.choice(multipliers)
    win = bet * result_mult

    if win > 0:
        update_balance(user_id, win)
        bot.send_message(message.chat.id, f"🎡 Multiplier: <b>{result_mult}x</b>! You got <b>+${win:.2f}</b>.")
    else:
        bot.send_message(message.chat.id, "🎡 Multiplier: <b>0x</b>. Lost your bet!")

if __name__ == "__main__":
    logger.info("Bot starting...")
    bot.infinity_polling(skip_pending=True)
