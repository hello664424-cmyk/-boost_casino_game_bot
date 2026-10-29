import os
import random
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory database (Use a real DB like SQLite or PostgreSQL for production)
USER_BALANCES = {}
DEFAULT_BALANCE = 1000

def get_balance(user_id: int) -> int:
    return USER_BALANCES.get(user_id, DEFAULT_BALANCE)

def update_balance(user_id: int, amount: int):
    USER_BALANCES[user_id] = get_balance(user_id) + amount

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in USER_BALANCES:
        USER_BALANCES[user.id] = DEFAULT_BALANCE

    welcome_text = (
        f"👋 Welcome, {user.first_name}!\n\n"
        f"🎰 **Casino & Games Bot** 🎲\n"
        f"💰 Your Current Balance: **{get_balance(user.id)}** coins\n\n"
        f"Choose an option below to start playing or boost your coins!"
    )

    keyboard = [
        [
            InlineKeyboardButton("🎲 Roll Dice (100 coins)", callback_data="play_dice"),
            InlineKeyboardButton("🎰 Slot Machine (100 coins)", callback_data="play_slots"),
        ],
        [
            InlineKeyboardButton("🎁 Claim Daily Bonus", callback_data="daily_bonus"),
            InlineKeyboardButton("💳 Check Balance", callback_data="check_balance"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id
    current_balance = get_balance(user_id)

    if query.data == "check_balance":
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        await query.edit_message_text(
            f"💰 **Your Balance:** {current_balance} coins",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "daily_bonus":
        update_balance(user_id, 500)
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        await query.edit_message_text(
            f"🎁 **Daily Bonus Claimed!**\n\n"
            f"You received **+500 coins**.\n"
            f"New Balance: **{get_balance(user_id)} coins**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "play_dice":
        if current_balance < 100:
            keyboard = [[InlineKeyboardButton("🎁 Claim Daily Bonus", callback_data="daily_bonus")]]
            await query.edit_message_text(
                "❌ **Insufficient Coins!** You need at least 100 coins to roll.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        update_balance(user_id, -100)
        # Send native Telegram Dice animation
        msg = await context.bot.send_dice(chat_id=query.message.chat_id, emoji="🎲")
        await asyncio.sleep(3)

        dice_val = msg.dice.value
        if dice_val >= 4:
            win_amount = 200
            update_balance(user_id, win_amount)
            result_text = f"🎉 **You won!** Rolled a {dice_val}.\n+200 coins added!"
        else:
            result_text = f"💔 **You lost!** Rolled a {dice_val}.\nBetter luck next time!"

        keyboard = [
            [InlineKeyboardButton("🎲 Play Again", callback_data="play_dice")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")],
        ]
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"{result_text}\n\n💰 New Balance: **{get_balance(user_id)} coins**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "play_slots":
        if current_balance < 100:
            keyboard = [[InlineKeyboardButton("🎁 Claim Daily Bonus", callback_data="daily_bonus")]]
            await query.edit_message_text(
                "❌ **Insufficient Coins!** You need at least 100 coins to play.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        update_balance(user_id, -100)
        # Send native Telegram Slot Machine animation
        msg = await context.bot.send_dice(chat_id=query.message.chat_id, emoji="🎰")
        await asyncio.sleep(2)

        # Telegram slot values range 1 to 64; 64 is the jackpot (777)
        slot_val = msg.dice.value
        if slot_val == 64:
            win_amount = 1000
            update_balance(user_id, win_amount)
            result_text = "💥 **JACKPOT! 777!** 💥\n+1000 coins added!"
        elif slot_val in [1, 22, 43]:  # Specific combinations for small wins
            win_amount = 250
            update_balance(user_id, win_amount)
            result_text = f"🎉 **Nice Hit!**\n+{win_amount} coins added!"
        else:
            result_text = "💔 **No match!** Try again."

        keyboard = [
            [InlineKeyboardButton("🎰 Spin Again", callback_data="play_slots")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")],
        ]
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"{result_text}\n\n💰 New Balance: **{get_balance(user_id)} coins**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "main_menu":
        keyboard = [
            [
                InlineKeyboardButton("🎲 Roll Dice (100 coins)", callback_data="play_dice"),
                InlineKeyboardButton("🎰 Slot Machine (100 coins)", callback_data="play_slots"),
            ],
            [
                InlineKeyboardButton("🎁 Claim Daily Bonus", callback_data="daily_bonus"),
                InlineKeyboardButton("💳 Check Balance", callback_data="check_balance"),
            ],
        ]
        await query.edit_message_text(
            f"🎰 **Casino & Games Bot** 🎲\n"
            f"💰 Your Current Balance: **{get_balance(user_id)}** coins\n\n"
            f"Select an option to play:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN environment variable not found!")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
