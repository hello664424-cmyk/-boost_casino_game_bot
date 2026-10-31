import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Fetch Token from environment variables (Railway requirement)
TOKEN = os.getenv("BOT_TOKEN")

# Simple in-memory user database
# Format: {user_id: {"balance": int, "daily_claimed": bool}}
USERS = {}

def get_user_data(user_id: int):
    """Retrieve or initialize user data."""
    if user_id not in USERS:
        USERS[user_id] = {"balance": 1000, "daily_claimed": False}  # Starter balance
    return USERS[user_id]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message with main menu."""
    user = update.effective_user
    user_data = get_user_data(user.id)
    
    keyboard = [
        [
            InlineKeyboardButton("🎰 Slots", callback_data="game_slots"),
            InlineKeyboardButton("🎲 Dice", callback_data="game_dice"),
        ],
        [
            InlineKeyboardButton("🎳 Bowling", callback_data="game_bowling"),
            InlineKeyboardButton("🎯 Darts", callback_data="game_darts"),
        ],
        [
            InlineKeyboardButton("🏀 Basketball", callback_data="game_basket"),
            InlineKeyboardButton("⚽ Football", callback_data="game_football"),
        ],
        [
            InlineKeyboardButton("💰 Balance", callback_data="user_balance"),
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="user_daily"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"👋 Welcome to the Casino & Boost Bot, *{user.first_name}*!\n\n"
        f"💵 Your Balance: *{user_data['balance']} Coins*\n"
        "Choose a game below to play and boost your points!"
    )

    if update.message:
        await update.message.reply_text(
            welcome_text, parse_mode="Markdown", reply_markup=reply_markup
        )
    elif update.callback_query:
        await update.callback_query.message.edit_text(
            welcome_text, parse_mode="Markdown", reply_markup=reply_markup
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle menu and game callback queries."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    bet_amount = 50

    if query.data == "user_balance":
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        await query.message.edit_text(
            f"💳 *User Profile*\n\n"
            f"👤 User: {query.from_user.first_name}\n"
            f"💰 Balance: *{user_data['balance']} Coins*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if query.data == "user_daily":
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        if not user_data["daily_claimed"]:
            user_data["balance"] += 200
            user_data["daily_claimed"] = True
            msg = "🎁 You claimed your daily reward of *200 Coins*!"
        else:
            msg = "⚠️ You have already claimed your daily reward today."
            
        await query.message.edit_text(
            msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if query.data == "main_menu":
        await start(update, context)
        return

    # Game Handling Logic
    if user_data["balance"] < bet_amount:
        keyboard = [[InlineKeyboardButton("🎁 Claim Daily Bonus", callback_data="user_daily")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        await query.message.edit_text(
            f"❌ *Insufficient Balance!*\n\nYou need at least {bet_amount} Coins to play.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Deduct bet before sending roll
    user_data["balance"] -= bet_amount

    # Map buttons to Telegram animated dice emojis
    emoji_map = {
        "game_slots": "🎰",
        "game_dice": "🎲",
        "game_bowling": "🎳",
        "game_darts": "🎯",
        "game_basket": "🏀",
        "game_football": "⚽",
    }

    selected_emoji = emoji_map.get(query.data)

    if selected_emoji:
        # Send native animated Telegram dice
        msg = await context.bot.send_dice(
            chat_id=query.message.chat_id, emoji=selected_emoji
        )
        score = msg.dice.value

        # Calculate winnings based on native dice score rules
        winnings = 0
        if selected_emoji == "🎰":  # Slots (Values 1 to 64; 64 = 777 jackpot)
            if score == 64:
                winnings = 500  # Jackpot 777
            elif score in [1, 22, 43]:
                winnings = 150
        elif selected_emoji == "🎲":  # Standard 6-sided dice
            if score >= 4:
                winnings = bet_amount * 2
        elif selected_emoji in ["🎳", "🎯", "🏀", "⚽"]:  # High scores represent success
            if score >= 5:
                winnings = bet_amount * 2

        user_data["balance"] += winnings

        # Result Summary
        result_text = (
            f"🎮 *Game Result*\n"
            f"Bet: `{bet_amount} Coins` | Score: `{score}`\n\n"
        )
        if winnings > 0:
            result_text += f"🎉 *WIN!* You won *{winnings} Coins*!"
        else:
            result_text += "❌ *LOSS!* Better luck next time."

        result_text += f"\n\n💰 Current Balance: *{user_data['balance']} Coins*"

        keyboard = [
            [InlineKeyboardButton("🔄 Play Again", callback_data=query.data)],
            [InlineKeyboardButton("📋 Menu", callback_data="main_menu")],
        ]
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=result_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


def main():
    """Start the bot."""
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
