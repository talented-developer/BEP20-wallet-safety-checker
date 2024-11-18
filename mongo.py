import os
from pymongo import MongoClient
import time

# MongoDB setup
mongo_client = MongoClient(os.getenv("MONGODB_URI"))
db = mongo_client['wallet_db']  # Replace with your database name
collection = db['users']  # Replace with your collection name

def find_user(user_id):
    """Find a user by user_id."""
    return collection.find_one({"user_id": user_id})

def add_or_update_user(user_id, wallet_address):
    """Add a new user or update an existing user's wallet address."""
    collection.update_one({"user_id": user_id}, {"$set": {"wallet_address": wallet_address}}, upsert=True)

def add_payment_info(user_id, timestamp, value):
    collection.update_one({"user_id": user_id}, {"$set": {"payment_time": timestamp, "payment_value": value}}, upsert=True)

def check_user_paid(user_id):
    user = collection.find_one({"user_id": user_id})
    current_timestamp = time.time()

    try:
        if(current_timestamp - user['payment_time'] < 30 * 60 * 1000):
            return True
        else:
            return False
    except:
        return False 