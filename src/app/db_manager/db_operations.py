from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
import hashlib
from dotenv import load_dotenv
from typing import Dict, Optional
import os,json
from pathlib import Path


class DatabaseOperations:
    """DatabaseOperations: MongoDB helper for doctor credential management.

    Loads connection settings from a .env file (default: .env.doctors), connects to the specified MongoDB database and collection, ensures the login collection exists, and provides simple user operations:
    - insert_user(doc_username, password): store a new user with a hashed password.
    - find_user(doc_username, password): verify credentials by matching hashed password.

    Notes:
    - Passwords are hashed with SHA-256 (replace with bcrypt/argon2 for production).
    - Avoid printing secrets and ensure proper error handling in production.
    """
    
    def __init__(self, env_file=None):
        """
        :param env_file: Path or str to .env file. If None, defaults to sibling .env.doctors.
        """
        
        # resolve env_file to a Path before using .is_file()
        if env_file is None:
            env_path = Path(__file__).parent / ".env.doctors"
        else:
            env_path = Path(env_file)

        if env_path.is_file():
            load_dotenv(env_path)
            print(f"Loaded environment variables from: {env_path}")
        else:
            raise RuntimeError(f".env file not found: {env_path}")

        client_url = os.getenv("MONGODB_CLIENT_URL")
        db_name = os.getenv("MONGODB_DB_NAME")
        collection_name = os.getenv("MONGODB_COLLECTION_NAME")

        missing = [n for n, v in (("MONGODB_CLIENT_URL", client_url),
                                ("MONGODB_DB_NAME", db_name),
                                ("MONGODB_COLLECTION_NAME", collection_name)) if not v]
        if missing:
            raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

        try:
            # quick fail if server unreachable
            self.client = MongoClient(client_url, serverSelectionTimeoutMS=5000)
            self.client.admin.command("ping")
            self.db = self.client[db_name]
            self.collection_name = self.create_collection(collection_name)
            self.collection = self.db[collection_name]
            
        except ConnectionFailure as exc:
            raise RuntimeError("Failed to connect to MongoDB") from exc

    def create_collection(self,collection="doc_logins"):
        # Ensure the collection exists
        if collection not in self.db.list_collection_names():
            self.db.create_collection(collection)
        return collection

    def insert_record(self, user_document: Dict):
        # Create a user document
        if not user_document:
            print ("!!WARNING!! Empty user data!! nothing to enter in database!!")
            return None
        else:
            # Insert the user into the collection
            result = self.collection.insert_one(user_document)
            return result.inserted_id  # Return the new user's ID
        
    def update_record(self, primary_key_name: str, primary_key_val: str, updates: Dict) -> Dict:
        """
        Update a user document identified by doc_username with fields from updates.

        :param primary_key_name: primary key field name of the collection to update ( eg :"doc_id")
        :param primary_key_val: primary_key_val of the record to update (eg : matches value of "doc_id" field)
        :param updates: dict of fields to set (e.g., {"email": "new@example.com"})
        :return: dict with result info: {"matched_count": int, "modified_count": int, "acknowledged": bool}
        """
        if not primary_key_name or not primary_key_val:
            raise ValueError("REQUIRED : Primary key name or vale is missing !!")
        if not updates or not isinstance(updates, dict):
            raise ValueError("updates must be a non-empty dict")

        result = self.db[self.collection_name].update_one(
            {primary_key_name : primary_key_val},
            {"$set": updates},
            upsert=False
        )

        return {
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "acknowledged": result.acknowledged
        }

    
    #Helper functions for uniqueness checks
    def find_by_email(self, email: str) -> Optional[Dict]:
        if not email: return None
        check = self.db[self.collection_name].find_one({"email": email.strip()})
        print("Email check against mongo =")
        print(check)
        
        return check

    def find_by_license(self, license_no: str) -> Optional[Dict]:
        if not license_no: return None
        check = self.db[self.collection_name].find_one({"license": license_no.strip()})
        print("License check against mongo =")
        print(check)
        return check

    def find_user(self, doc_username, password):
        # Hash the password for verification
        hashed_password = self.hash_password(password)
        
        # Check if the user exists with the correct username and password
        user = self.collection.find_one({
            "doc_username": doc_username,
            "hashed_password": hashed_password,
            "password": password
        })
        return user
    
    def find_by_id(self, id_val: str, id_field: str) -> Optional[Dict]:
        """
        :param id_val : value of primary key to be searched
        :param id_field : primary key field name to be searched
        """
        if not id_field or not id_val: return None
        return self.db[self.collection_name].find_one({id_field: id_val})





