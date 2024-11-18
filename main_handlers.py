import os
import asyncio
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from datetime import datetime
from mongo import find_user, add_or_update_user, check_user_paid
from main_utils import get_bep20_transactions, classify_transactions, calculate_balance_and_usd, verify_user_payment

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user = find_user(user_id)  # Fetch the user from the database
    
    keyboard = []
    
    if user:
        wallet_address = user['wallet_address']
        keyboard.append([InlineKeyboardButton("💰 View balance and transactions", callback_data='check_valid_transactions')])
        keyboard.append([InlineKeyboardButton("✅ Safety check", callback_data='check_invalid_transactions')])
        keyboard.append([InlineKeyboardButton("🔄 Change Wallet Address", callback_data='change_wallet')])
    else:
        keyboard.append([InlineKeyboardButton("✏️ Register Wallet Address", callback_data='set_wallet')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # await update.message.reply_photo(photo=open('img/mark.webp', 'rb'))  # Send image

    try:
        with open('img/mark.webp', 'rb') as photo:
            await update.message.reply_photo(photo=photo)
    except Exception as e:
        print(f"Error occurred: {str(e)}")

    await update.message.reply_text(
        f"🗓 Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "👋 Welcome!\n\n Check the safety of your wallet normally and manage all your financial assets safely.\n\n"
        f"💼 Your BEP20 Wallet Address: {user['wallet_address'] if user else '❌ Not set'}\n",
        reply_markup=reply_markup
    )

    # Send the user's ID to the admin
    admin_user_id = os.getenv("ADMIN_ID")
    await context.bot.send_message(chat_id=admin_user_id, text=f"User({user_id}) started the bot.")


async def set_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("👇 Please send me your BEP20 wallet address.")

async def change_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("👇 Please send me your new BEP20 wallet address.")

async def check_valid_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    user_id = update.effective_user.id
    user = find_user(user_id)

    if user:
        response_message = (
            "⏳ Please wait a moment while we get all the valid transactions made using your wallet from the BSC blockchain network.\n\n"
            "🔍 The longer your wallet has been created and the more transactions your wallet has had, the longer it will take to search for transactions from your wallet."
        )
        await update.callback_query.message.reply_text(response_message)

        wallet_address = user['wallet_address']
        transactions = get_bep20_transactions(wallet_address)
        
        valid_transactions, invalid_transactions = classify_transactions(transactions, wallet_address)
        total_balance = calculate_balance_and_usd(valid_transactions, wallet_address)

        valid_tokens_env = os.getenv('VALID_TOKENS', '')
        valid_tokens = valid_tokens_env.split(',') if valid_tokens_env else []

        response_message = "\n💰 Total Balance:\n\n"

        for token in valid_tokens:
            if total_balance[token] != 0:
                response_message += f"{token}: {total_balance[token]}\n"

        await update.callback_query.message.reply_text(response_message, parse_mode='Markdown')

        response_message = f"✅ Total Valid Transactions: {len(valid_transactions)}\n\n"

        message_count = 0
        for tx in valid_transactions:
            transaction_date = datetime.utcfromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S')
            in_out_symbol = ""
            if wallet_address == tx['from']:
                in_out_symbol = "💳➡️"
            if wallet_address == tx['to']:
                in_out_symbol = "➡️💳"
            response_message += (f"{in_out_symbol} Hash: `{tx['hash']}`, From: `{tx['from']}`, To: `{tx['to']}`, "
                                 f"Value: `{int(tx['value']) / (10 ** int(tx['tokenDecimal'])):.6f} {tx['tokenSymbol']}`, "
                                 f"Date: `{transaction_date}` {tx['nonce']}\n")
            message_count+=1
            if message_count == 15:
                try:
                    await update.callback_query.message.reply_text(response_message, parse_mode='Markdown')
                except telegram.error.RetryAfter as e:
                    await update.callback_query.message.reply_text("⏳ Please wait a moment", parse_mode='Markdown')
                    await asyncio.sleep(e.retry_after)
                    await update.callback_query.message.reply_text(response_message, parse_mode='Markdown')
                message_count = 0
                response_message = ""
                await asyncio.sleep(1)

        if response_message != "":
            await update.callback_query.message.reply_text(response_message, parse_mode='Markdown')
    else:
        await update.callback_query.message.reply_text("❌ No wallet address found.")

async def check_invalid_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    user_id = update.effective_user.id
    user = find_user(user_id)

    if user:
        if check_user_paid(user_id):
            response_message = "⏳ Please wait a moment while we retrieve and analyze all invalid transactions made using your wallet from the BSC blockchain network.\n\nThe longer your wallet has been created and the more transactions your wallet has had, the longer it will take to search for transactions from your wallet."
            await update.callback_query.message.reply_text(response_message)

            wallet_address = user['wallet_address']
            transactions = get_bep20_transactions(wallet_address)
            
            valid_transactions, invalid_transactions = classify_transactions(transactions, wallet_address)

            response_message = f"❌ Total Invalid Transactions: {len(invalid_transactions)}\n"
            response_message += "\n📜 Invalid Transactions:\n"
            
            message_count = 0
            # valid_tokens =  ['BSC-USD', 'USDC', 'USDT', 'LDOGE', 'BNB']
            # valid_tokens_env = os.getenv('VALID_TOKENS', '')
            # valid_tokens = valid_tokens_env.split(',') if valid_tokens_env else []
            invalid_tokens = []
            spam_transactions_count = 0

            for tx in invalid_transactions:
                transaction_date = datetime.utcfromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S')
                transaction_value = int(tx['value']) / (10 ** int(tx['tokenDecimal']))
                # if tx['tokenSymbol'] not in valid_tokens:
                in_out_symbol = ""
                if wallet_address == tx['from']:
                    in_out_symbol = "💳➡️"
                if wallet_address == tx['to']:
                    in_out_symbol = "➡️💳"
                if transaction_value > 0:
                    response_message += (f"{in_out_symbol} Hash: `{tx['hash']}`, From: `{tx['from']}`, To: `{tx['to']}`, "
                                        f"Value: `{transaction_value:.6f} {tx.get('tokenSymbol', 'N/A')}`, "
                                        f"Date: `{transaction_date}`\n")
                    if tx['tokenSymbol'] not in invalid_tokens:
                        invalid_tokens.append(tx['tokenSymbol'])
                    message_count+=1
                    spam_transactions_count+=1
                    if message_count == 15:
                        try:
                            await update.callback_query.message.reply_text(response_message, parse_mode='Markdown')
                        except telegram.error.RetryAfter as e:
                            await update.callback_query.message.reply_text("⏳ Please wait a moment", parse_mode='Markdown')
                            await asyncio.sleep(e.retry_after)
                            await update.callback_query.message.reply_text(response_message, parse_mode='Markdown')
                        message_count = 0
                        response_message = ""
                        await asyncio.sleep(1)
                
            if response_message != "":
                await update.callback_query.message.reply_text(response_message, parse_mode='Markdown')

            response_message = (f"⚠️ Never go to the site included in the fake token!\n\n Suspicious tokens: {len(invalid_tokens)}\n\n") 
            token_no = 0
            for token in invalid_tokens:
                token_no += 1
                response_message += (f"{token_no}. {token.replace('.','[dot]')}\n")

            await update.callback_query.message.reply_text(response_message)

            if len(invalid_tokens) == 0:
                response_message = "✅ As you can see, your BEP20 wallet is safe.\n\n"
                response_message += "🔒 There is no attempt or trace of any hacking and there are no spam transactions."
                await update.callback_query.message.reply_text(response_message)
            else:
                response_message = (
                    f"⚠️ As you can see, there were {spam_transactions_count} intentionally "
                    "invalid transactions using your wallet, including spam transactions.\n\n"
                    "🚨 Some invalid token strings also contain forged ASCII characters.\n"
                    "⚠️ Spam transactions can be made using valid tokens (e.g. USDC) or they "
                    "can be made using invalid or fraudulent tokens.\nSome of them are likely "
                    "to show signs of hacking attempts or attempts to target your wallet.\n"
                    "Most spam transactions significantly reduce the security of your wallet.\n"
                )
                await update.callback_query.message.reply_text(response_message)
                response_message = (
                    "If the spam transactions are connected to illegitimate tokens or untrustworthy projects, "
                    "those tokens can cause problems for your wallet.\n\n🔒 Your wallet is therefore not secure.\n\n"
                    "🚨 We recommend that you transfer funds from your BEP20 wallet to another safe and reliable wallet at the appropriate time.\n\n"
                    # "ℹ️  You may see many invalid transactions from your wallet on some sites, but most sites do not show invalid transactions, "
                    # "which are difficult to analyze.\nHowever, we show all invalid transactions except valid transactions and invalid "
                    # "transactions with zero volume.\n🌟 This provides the most objective information about the wallet."
                )
                await update.callback_query.message.reply_text(response_message)

            admin_user_id = os.getenv("ADMIN_ID")
            await context.bot.send_message(chat_id=admin_user_id, text=f"User({user_id}) checked safety of his wallet.\nHis wallet address is `{wallet_address}`")
        else:
            admin_wallet_address = os.getenv("WALLET_ADDRESS")
            response_message = (
                "⚠️ You need to pay at least 10 USDT to check the security of your wallet.\n\n"
                "🚨 To continue, please read and follow the instructions below carefully.\n\n"
                "After completing the payment, please enter the hash value of the transaction that reflects the payment.\n"
                "You can check the security of your wallet within 30 minutes from the time you completed the payment.\n"
                "Once the time expires, you can pay 10 USDT again to check the security of your wallet.\n"
            )
            await update.callback_query.message.reply_text(response_message)
            response_message = (
                "The older your wallet has been created and the more transactions have been "
                "made with your wallet, the longer it will take to get and check all the transactions.\n"
                "For example, it takes about 5 minutes including the waiting time to check a wallet with "
                "10,000 transactions.\nPlease check your wallet and send us your feedback after seeing the results.\n"
                "ℹ️  The email address is anat.fulldev@gmail.com.\n\n"
            )
            await update.callback_query.message.reply_text(response_message)
            response_message = (
                "🎉 Would you like to check the security of your wallet?\n\n"
                f"💳 Our Tether USD Address on BSC Network is as follows.\n\n`{admin_wallet_address}`\n\n"
                "💵 You can also pay with USDC instead of USDT.\n\n"
                "🚨 After completing the payment, please enter the hash value of the payment "
                "below👇👇👇 and click the check button again on the home screen."
            )
            await update.callback_query.message.reply_text(response_message, parse_mode='Markdown')

    else:
        await update.callback_query.message.reply_text("❌ No wallet address found.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if update.message.text.startswith('0x') and len(update.message.text) == 42:  # Valid wallet address
        wallet_address = update.message.text.strip()
        add_or_update_user(user_id, wallet_address)
        await update.message.reply_text("✅ Wallet address updated/set successfully!")
        
        await asyncio.sleep(3)

        # Automatically call start function after setting wallet address
        await start(update, context)

    elif update.message.text.startswith('0x') and len(update.message.text) == 66:  # Valid hash code
        hash_code = update.message.text.strip()
        user = find_user(user_id)
        
        await update.message.reply_text("⏳ Please wait a moment while we verify your transaction.")
        
        verify_result = verify_user_payment(user_id, user['wallet_address'], hash_code)
        
        if verify_result:
            response_message = "✅ Your payment has been verified correctly.\n\n🔄 To check the safety of your wallet, please click the check button again on the home screen within 30 minutes."
            await update.message.reply_text(response_message)
            
            await asyncio.sleep(3)

            # Automatically call start function after verifying payment
            await start(update, context)
            
        else:
            response_message = "❌ Your payment could not be verified.\n\n🙏 Please check the hash code again and enter it again."
            await update.message.reply_text(response_message)

    else:
        await update.message.reply_text("❗ Please enter a valid BEP20 wallet address starting with '0x'.")

# Ensure to register handle_message in your dispatcher for handling text messages.