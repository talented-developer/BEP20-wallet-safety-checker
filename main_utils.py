import os
import requests
from datetime import datetime
from mongo import add_payment_info

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
    out_nonces = []

    # Open a file to write transaction details
    # with open('transactions_log.txt', 'a') as log_file:  # Append mode
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
        nonce_valid = True
        in_out_type = "in"
        dt = datetime.fromtimestamp(int(tx['timeStamp']))
        
        if from_address == wallet_address.lower():
            nonce_valid = False
            in_out_type = "out"
        if token_symbol in valid_tokens:
            if(dt.year<2022 or (dt.year==2022 and dt.month==1)):
                if value > 0 and (nonce - tokens_nonce >= 0 and nonce - tokens_nonce <= 5) :
                    nonce_valid = True
                    tokens_nonce = nonce
            else:
                if from_address == wallet_address.lower():
                    if value > 0 and (nonce - tokens_nonce >= -2) and (nonce - tokens_nonce <= 3) and (nonce not in out_nonces):
                        if nonce - tokens_nonce < 0:
                            # print("============= here!==============", nonce, tokens_nonce)
                            back_no = 0
                            while(1):
                                back_no -= 1
                                # print("===============", int(valid_transactions[back_no]['nonce']))
                                if (len(valid_transactions) + back_no > 0) and (valid_transactions[back_no]['from'] == wallet_address) and (int(valid_transactions[back_no]['nonce']) > nonce):
                                    pre_tx = valid_transactions.pop(back_no)
                                    invalid_transactions.append(pre_tx)
                                    # print("============", pre_tx['nonce'],"=============")
                                    back_no += 1
                                if (len(valid_transactions) + back_no > 0) and (valid_transactions[back_no]['from'] == wallet_address) and (int(valid_transactions[back_no]['nonce']) < nonce):
                                    break
                                if len(valid_transactions) + back_no == 0:
                                    break
                        nonce_valid = True
                        tokens_nonce = nonce
                        out_nonces.append(nonce)

        # if token_symbol == 'BNB':
        # print(tx_hash,from_address,to_address,value,tx['tokenDecimal'],confirmations,token_symbol,datetime.fromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S'),tx['blockNumber'],tx['gasUsed'],tx['gasPrice'],tx['input'],status,tx['nonce'])

        # print(value,token_symbol,datetime.fromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S'),tx['blockNumber'],tx['nonce'],in_out_type)

        # transaction_log_entry = (
        #     f"Hash: {tx_hash}, From: {from_address}, To: {to_address}, "
        #     f"Value: {value:.6f}, Token Decimal: {decimal}, Confirmations: {confirmations}, "
        #     f"Token Symbol: {token_symbol}, Time: {datetime.fromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S')}, "
        #     f"Block Number: {tx['blockNumber']}, Gas Used: {tx['gasUsed']}, "
        #     f"Gas Price: {tx['gasPrice']}, Input: {tx['input']}, Status: {status}, Nonce: {nonce}\n"
        # )

        # # Write the transaction log entry to the file
        # log_file.write(transaction_log_entry)

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
        if tx['from'] == wallet_address.lower():
            total_balance[tx['tokenSymbol']] -= value_in_tokens
            
    return total_balance

def verify_user_payment(user_id, wallet_address, hash_code):
    admin_wallet_address = os.getenv("WALLET_ADDRESS")
    transactions = get_bep20_transactions(admin_wallet_address.lower())

    valid_tokens_env = os.getenv('VALID_TOKENS', '')
    valid_tokens = valid_tokens_env.split(',') if valid_tokens_env else []
    payment_tokens = ['BSC-USD', 'USDC']
    tokens_nonce = 0

    result = False

    for tx in transactions:
        tx_hash = tx['hash']
        from_address = tx['from']
        to_address = tx['to']
        value = int(tx['value']) / (10 ** int(tx['tokenDecimal']))  # Convert value to human-readable format
        confirmations = int(tx['confirmations'])
        token_symbol = tx['tokenSymbol']
        nonce = int(tx['nonce'])

        if tx_hash == hash_code and from_address == wallet_address and to_address == admin_wallet_address.lower():
            if token_symbol in payment_tokens and value >= 10:
                add_payment_info(user_id, int(tx['timeStamp']), value)
                result = True

    return result