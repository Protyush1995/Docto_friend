from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
import hashlib

class DatabaseOperations:
    def __init__(self, db_name='doctor_mate'):
        # Initialize the MongoDB client and select the database
        try:
            self.client = MongoClient('mongodb://localhost:27017/')
            self.db = self.client[db_name]
            self.collection = self.db['doc_logins']
            self.create_collection()
            print("Connected to the database:")
            print(f"Database: {db_name}")
            print(f"Collection: 'doc_logins'")
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

# Example usage
if __name__ == "__main__":
    db_ops = DatabaseOperations()
    # To add a new user
    user_id = db_ops.insert_user('test_user', 'test_password')
    print(f'Inserted user with ID: {user_id}')

    # To find a user
    user = db_ops.find_user('test_user', 'test_password')
    print(f'User found: {user}') if user else print('User not found')
