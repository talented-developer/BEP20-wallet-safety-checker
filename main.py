import os
import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()

# MongoDB setup
mongo_client = MongoClient(os.getenv("MONGODB_URI"))
db = mongo_client['wallet_db']  # Replace with your database name
collection = db['users']  # Replace with your collection name

# Function to start the bot and show options
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # Check if user exists in the database
    user = collection.find_one({"user_id": user_id})
    
    keyboard = []
    
    if user:
        # User has a wallet address
        wallet_address = user['wallet_address']
        keyboard.append([InlineKeyboardButton("Check safety of my wallet", callback_data='check_wallet')])
        keyboard.append([InlineKeyboardButton("Change bep20 wallet address", callback_data='change_wallet')])
    else:
        # User does not have a wallet address
        keyboard.append([InlineKeyboardButton("Set bep20 wallet address", callback_data='set_wallet')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Welcome! Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nYour Wallet Address: {user['wallet_address'] if user else 'Not set'}", reply_markup=reply_markup)

# Function to handle setting a new wallet address
async def set_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Please send me your BEP20 wallet address.")

async def change_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Please send me your new BEP20 wallet address.")

async def check_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    user_id = update.effective_user.id
    
    user = collection.find_one({"user_id": user_id})
    
    if user:
        wallet_address = user['wallet_address']
        transactions = get_bep20_transactions(wallet_address)
        
        valid_transactions, invalid_transactions = classify_transactions(transactions)
        
        total_balance, total_usd_value = calculate_balance_and_usd(valid_transactions)
        
        response_message = f"Total Valid Transactions: {len(valid_transactions)}\nTotal Balance: {total_balance:.6f} BSC-USD\nTotal USD Value: ${total_usd_value:.2f}\n\n"
        
        # Display valid transactions details
        response_message += "Valid Transactions:\n"
        for tx in valid_transactions:
            transaction_date = datetime.utcfromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S')
            response_message += (f"Hash: {tx['hash']}, From: {tx['from']}, To: {tx['to']}, "
                                 f"Value: {int(tx['value']) / (10 ** int(tx['tokenDecimal'])):.6f} {tx['tokenSymbol']}, "
                                 f"Date: {transaction_date}\n")
        
        await update.callback_query.message.reply_text(response_message)
        # Display invalid transactions details
        response_message = f"Total Valid Transactions: {len(invalid_transactions)}\n"
        response_message += "\nInvalid Transactions:\n"
        for tx in invalid_transactions:
            transaction_date = datetime.utcfromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S')
            response_message += (f"Hash: {tx['hash']}, From: {tx['from']}, To: {tx['to']}, "
                                 f"Value: {int(tx['value']) / (10 ** int(tx['tokenDecimal'])):.6f} {tx.get('tokenSymbol', 'N/A')}, "
                                 f"Date: {transaction_date}\n")
        
        await update.callback_query.message.reply_text(response_message)
    else:
        await update.callback_query.message.reply_text("No wallet address found.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # Check if the message is a valid wallet address input
    if update.message.text.startswith('0x') and len(update.message.text) == 42:
        wallet_address = update.message.text.strip()
        
        # Check if user already exists in the database
        user = collection.find_one({"user_id": user_id})
        
        if user:
            # Update existing user's wallet address
            collection.update_one({"user_id": user_id}, {"$set": {"wallet_address": wallet_address}})
            await update.message.reply_text("Wallet address updated successfully!")
        else:
            # Insert new user's wallet address into the database
            collection.insert_one({"user_id": user_id, "wallet_address": wallet_address})
            await update.message.reply_text("Wallet address set successfully!")
            
    else:
        await update.message.reply_text("Please enter a valid BEP20 wallet address starting with '0x'.")

def get_bep20_transactions(wallet_address):
    """Fetch all BEP20 transactions for a given wallet address."""
    transactions = []
    start_block = 0
    end_block = 99999999
    page = 1
    offset = 100  # Number of transactions per request

    while True:
        url = f'https://api.bscscan.com/api?module=account&action=tokentx&address={wallet_address}&startblock={start_block}&endblock={end_block}&page={page}&offset={offset}&sort=asc&apikey={os.getenv("API_KEY")}'
        
        response = requests.get(url)
        data = response.json()

        if data['status'] == '1':
            transactions.extend(data['result'])
            if len(data['result']) < offset:
                break  # No more transactions to fetch
            page += 1  # Move to the next page
        else:
            print("Error fetching data:", data.get('message', 'Unknown error'))
            break

    return transactions

def classify_transactions(transactions):
    """Classify transactions into valid and invalid based on specific criteria."""
    valid_transactions = []
    invalid_transactions = []

    for tx in transactions:
        tx_hash = tx['hash']
        from_address = tx['from']
        to_address = tx['to']
        value = int(tx['value']) / (10 ** int(tx['tokenDecimal']))  # Convert value to human-readable format
        confirmations = int(tx['confirmations'])
        token_symbol = tx['tokenSymbol']

        if (tx_hash and from_address and to_address and value > 0 
                and confirmations > 0 and token_symbol == 'BSC-USD'):
            valid_transactions.append(tx)
        else:
            invalid_transactions.append(tx)

    return valid_transactions, invalid_transactions

def calculate_balance_and_usd(valid_transactions):
    """Calculate total balance and USD value from valid transactions."""
    total_balance = 0.0
    total_usd_value = 0.0

    conversion_rates = {
        'BSC-USD': 1.0,  # Example conversion rate; replace with actual rates as needed.
        # Add other tokens and their conversion rates as necessary.
    }

    for tx in valid_transactions:
        value_in_tokens = int(tx['value']) / (10 ** int(tx['tokenDecimal']))
        
        total_balance += value_in_tokens
        
        token_symbol = tx['tokenSymbol']
        
        usd_value_per_token = conversion_rates.get(token_symbol, 0)
        
        total_usd_value += value_in_tokens * usd_value_per_token

    return total_balance, total_usd_value

if __name__ == "__main__":
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    application.add_handler(CommandHandler("start", start))
    
    application.add_handler(CallbackQueryHandler(set_wallet, pattern='set_wallet'))
    
    application.add_handler(CallbackQueryHandler(change_wallet, pattern='change_wallet'))
    
    application.add_handler(CallbackQueryHandler(check_wallet, pattern='check_wallet'))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until it is stopped by the user.
    import asyncio
    asyncio.run(application.run_polling())
