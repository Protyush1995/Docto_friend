from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
import hashlib
from dotenv import load_dotenv
import os
from pathlib import Path
class DatabaseOperations:
    def __init__(self, env_file=None):

        print(f"Current Working Directory: {os.getcwd()}") # Always load .env.doctors from the same folder as this file 
        if env_file is None: env_file = Path(__file__).parent / ".env.doctors" 
        if env_file.is_file(): 
            load_dotenv(env_file) 
            print(f"Loaded environment variables from: {env_file}") 
        else: 
            print(f"Warning: {env_file} not found!")
        client_url = os.getenv('MONGODB_CLIENT_URL') 
        db_name = os.getenv('MONGODB_DB_NAME') 
        collection_name = os.getenv('MONGODB_COLLECTION_NAME')
        # Print the values to check if they're loaded correctly
        print(f"Client URL: {client_url}")
        print(f"Database Name: {db_name}")
        print(f"Collection Name: {collection_name}")
        # Initialize the MongoDB client and select the database
        try:
            self.client = MongoClient(client_url)
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            self.create_collection()  # Ensure this method is defined
            print("Connected to the database:")
            print(f"Database: {db_name}")
            print(f"Collection: '{collection_name}'")
        except ConnectionFailure:
            print("Failed to connect to the database!")

    def create_collection(self):
        # Ensure the collection exists
        if 'doc_logins' not in self.db.list_collection_names():
            self.db.create_collection('doc_logins')

    def insert_user(self, doc_username, password):
        # Hash the password for security
        hashed_password = self.hash_password(password)

        # Create a user document
        user_document = {
            "_id": str(ObjectId()),  # Custom primary key (as a string)
            "doc_username": doc_username,
            "password": hashed_password
        }

        # Insert the user into the collection
        result = self.collection.insert_one(user_document)
        return result.inserted_id  # Return the new user's ID

    @staticmethod
    def hash_password(password):
        # Hash the password using SHA-256
        return hashlib.sha256(password.encode()).hexdigest()

    def find_user(self, doc_username, password):
        # Hash the password for verification
        hashed_password = self.hash_password(password)
        
        # Check if the user exists with the correct username and password
        user = self.collection.find_one({
            "doc_username": doc_username,
            "password": hashed_password
        })
        return user


