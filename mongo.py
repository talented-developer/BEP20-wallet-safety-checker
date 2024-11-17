import os
from pymongo import MongoClient

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

def check_user_paid(user_id):
    return False