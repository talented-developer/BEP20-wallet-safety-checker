import os
import asyncio
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder
from main_handlers import start, set_wallet, change_wallet, check_valid_transactions, check_invalid_transactions, handle_message
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes


# Load environment variables
load_dotenv()

def run_bot():
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(set_wallet, pattern='set_wallet'))
    application.add_handler(CallbackQueryHandler(change_wallet, pattern='change_wallet'))
    application.add_handler(CallbackQueryHandler(check_valid_transactions, pattern='check_valid_transactions'))
    application.add_handler(CallbackQueryHandler(check_invalid_transactions, pattern='check_invalid_transactions'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot
    asyncio.run(application.run_polling())

if __name__ == "__main__":
    run_bot()