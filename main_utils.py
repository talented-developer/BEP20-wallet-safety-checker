import os
import requests

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

def calculate_balance_and_usd(valid_transactions, wallet_address):
    """Calculate total balance and USD value from valid transactions."""
    total_balance = 0.0
    # total_usd_value = 0.0

    # conversion_rates = {
    #     'BSC-USD': 1.0,  # Example conversion rate; replace with actual rates as needed.
    # }

    for tx in valid_transactions:
        value_in_tokens = int(tx['value']) / (10 ** int(tx['tokenDecimal']))
                
        # token_symbol = tx['tokenSymbol']
        
        # usd_value_per_token = conversion_rates.get(token_symbol, 0)
        
        if tx['to'] == wallet_address.lower():
            total_balance += value_in_tokens
            # total_usd_value += value_in_tokens * usd_value_per_token
        else:
            total_balance -= value_in_tokens
            # total_usd_value -= value_in_tokens * usd_value_per_token
            
    # return total_balance, total_usd_value
    return total_balance