import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from datetime import datetime
from mongo import find_user, add_or_update_user
from main_utils import get_bep20_transactions, classify_transactions, calculate_balance_and_usd

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user = find_user(user_id)  # Fetch the user from the database
    
    keyboard = []
    
    if user:
        wallet_address = user['wallet_address']
        keyboard.append([InlineKeyboardButton("Check valid transactions", callback_data='check_valid_transactions')])
        keyboard.append([InlineKeyboardButton("Check invalid transactions", callback_data='check_invalid_transactions')])
        keyboard.append([InlineKeyboardButton("Change wallet address", callback_data='change_wallet')])
    else:
        keyboard.append([InlineKeyboardButton("Register wallet address", callback_data='set_wallet')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Welcome! Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nYour BEP20 Wallet Address: {user['wallet_address'] if user else 'Not set'}", 
        reply_markup=reply_markup
    )

async def set_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Please send me your BEP20 wallet address.")

async def change_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Please send me your new BEP20 wallet address.")

async def check_valid_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    user_id = update.effective_user.id
    user = find_user(user_id)

    if user:
        wallet_address = user['wallet_address']
        transactions = get_bep20_transactions(wallet_address)
        
        valid_transactions, invalid_transactions = classify_transactions(transactions)
        # total_balance, total_usd_value = calculate_balance_and_usd(valid_transactions, wallet_address)
        total_balance = calculate_balance_and_usd(valid_transactions, wallet_address)
        
        response_message = (
            f"Total Valid Transactions: {len(valid_transactions)}\n"
            f"Total Balance: {total_balance:.6f} BSC-USD\n\n"
            # f"Total USD Value: ${total_usd_value:.2f}\n\n"
        )

        response_message += "Valid Transactions:\n"
        message_count = 0
        for tx in valid_transactions:
            transaction_date = datetime.utcfromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S')
            response_message += (f"Hash: {tx['hash']}, From: {tx['from']}, To: {tx['to']}, "
                                 f"Value: {int(tx['value']) / (10 ** int(tx['tokenDecimal'])):.6f} {tx['tokenSymbol']}, "
                                 f"Date: {transaction_date}\n")
            message_count+=1
            if message_count == 10:
                await update.callback_query.message.reply_text(response_message)
                message_count = 0
                response_message = ""

        await update.callback_query.message.reply_text(response_message)
    else:
        await update.callback_query.message.reply_text("No wallet address found.")

async def check_invalid_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    user_id = update.effective_user.id
    user = find_user(user_id)

    if user:
        wallet_address = user['wallet_address']
        transactions = get_bep20_transactions(wallet_address)
        
        valid_transactions, invalid_transactions = classify_transactions(transactions)

        response_message = f"Total Invalid Transactions: {len(invalid_transactions)}\n"
        response_message += "\nInvalid Transactions:\n"
        
        message_count = 0
        for tx in invalid_transactions:
            transaction_date = datetime.utcfromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S')

            if tx['tokenSymbol'] != 'BSC-USD' and tx['tokenSymbol'] != 'UЅDТ':
                response_message += (f"Hash: {tx['hash']}, From: {tx['from']}, To: {tx['to']}, "
                                    f"Value: {int(tx['value']) / (10 ** int(tx['tokenDecimal'])):.6f} {tx.get('tokenSymbol', 'N/A')}, "
                                    f"Date: {transaction_date}\n")
                message_count+=1
                if message_count == 10:
                    await update.callback_query.message.reply_text(response_message)
                    message_count = 0
                    response_message = ""
            
        await update.callback_query.message.reply_text(response_message)
    else:
        await update.callback_query.message.reply_text("No wallet address found.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if update.message.text.startswith('0x') and len(update.message.text) == 42:
        wallet_address = update.message.text.strip()
        add_or_update_user(user_id, wallet_address)
        await update.message.reply_text("Wallet address updated/set successfully!")
    else:
        await update.message.reply_text("Please enter a valid BEP20 wallet address starting with '0x'.")