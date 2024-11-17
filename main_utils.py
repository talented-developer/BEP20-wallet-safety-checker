import os
import requests
from datetime import datetime

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

def classify_transactions(transactions, wallet_address):
    """Classify transactions into valid and invalid based on specific criteria."""
    valid_transactions = []
    invalid_transactions = []
    # valid_tokens =  ['BSC-USD', 'USDC', 'LDOGE', 'BNB']
    valid_tokens_env = os.getenv('VALID_TOKENS', '')
    valid_tokens = valid_tokens_env.split(',') if valid_tokens_env else []
    # tokens_nonce = {token: 0 for token in valid_tokens}
    tokens_nonce = 0

    for tx in transactions:
        tx_hash = tx['hash']
        from_address = tx['from']
        to_address = tx['to']
        value = int(tx['value']) / (10 ** int(tx['tokenDecimal']))  # Convert value to human-readable format
        confirmations = int(tx['confirmations'])
        token_symbol = tx['tokenSymbol']
        decimal = int(tx['tokenDecimal'])
        status = tx.get('status', 'unknown')
        nonce = int(tx['nonce'])
        if nonce == 0:
            nonce = 1
        nonce_valid = True
        
        if token_symbol in valid_tokens:
            if from_address == wallet_address.lower():
                nonce_valid = False
                if nonce - tokens_nonce == 1:
                    nonce_valid = True
                    tokens_nonce = nonce

        # if token_symbol == 'BNB':
        #     print(tx_hash,from_address,to_address,value,tx['tokenDecimal'],confirmations,token_symbol,datetime.fromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S'),tx['blockNumber'],tx['gasUsed'],tx['gasPrice'],tx['input'],status,tx['nonce'])

        if (tx_hash and from_address and to_address and value > 0 
                and confirmations > 0 and (token_symbol in valid_tokens) and nonce_valid):
            valid_transactions.append(tx)
        else:
            invalid_transactions.append(tx)

    return valid_transactions, invalid_transactions

def calculate_balance_and_usd(valid_transactions, wallet_address):
    """Calculate total balance and USD value from valid transactions."""
    valid_tokens_env = os.getenv('VALID_TOKENS', '')
    valid_tokens = valid_tokens_env.split(',') if valid_tokens_env else []
    total_balance = {token: 0.0 for token in valid_tokens}

    for tx in valid_transactions:
        value_in_tokens = int(tx['value']) / (10 ** int(tx['tokenDecimal']))
        
        if tx['to'] == wallet_address.lower():
            total_balance[tx['tokenSymbol']] += value_in_tokens
        else:
            total_balance[tx['tokenSymbol']] -= value_in_tokens
            
    return total_balance

def verify_user_payment(wallet_address, hash_code):
    return False