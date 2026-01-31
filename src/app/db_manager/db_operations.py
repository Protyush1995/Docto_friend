from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
import hashlib
from dotenv import load_dotenv,dotenv_values
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
            val = dotenv_values(env_path)
            #load_dotenv(env_path)
            print(f"DB LOG : Loading environment variables from: {env_path}")
        else:
            raise RuntimeError(f".env file not found: {env_path}")

        client_url = val.get("MONGODB_CLIENT_URL")
        db_name = val.get("MONGODB_DB_NAME")
        collection_name = val.get("MONGODB_COLLECTION_NAME")

        #Logging
        print(f"DB LOG : Loaded environment variables..........................")
        print(f"DB LOG : client_URL: {env_path}")
        print(f"DB LOG : DB Name: {db_name}")
        print(f"DB LOG : Collection Name:{collection_name}")


        missing = [n for n, v in (("MONGODB_CLIENT_URL", client_url),
                                ("MONGODB_DB_NAME", db_name),
                                ("MONGODB_COLLECTION_NAME", collection_name)) if not v]
        if missing:
            raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

        try:
            # quick fail if server unreachable
            self.client = MongoClient(client_url, serverSelectionTimeoutMS=5000)
            print("DB LOG : Trying mongodb connection.....")
            print(self.client.admin.command("ping"))
            self.db_name = db_name
            self.db = self.client[db_name]
            self.collection_name = collection_name
            self.collection = self.create_collection(collection_name) 
            print("DB LOG : Database class successfully initialized !")
            
        except ConnectionFailure as exc:
            raise RuntimeError("Failed to connect to MongoDB") from exc

    def create_collection(self,collection=None):

        if collection == None:
            collection = "doc_logins"

        # Ensure the collection exists
        if collection not in self.db.list_collection_names():
            self.db.create_collection(collection)
            print(f"DB LOG : Creating collection {collection} in database...")
        else : print(f"DB LOG : Collection {collection} already exists in database...")

        return self.db[collection]

    def insert_record(self, user_document: Dict):
        # Create a user document
        print(f"DB LOg : Received user Document ------ {json.dumps(user_document)}")
        if not user_document:
            print ("!!WARNING!! Empty user data!! nothing to enter in database!!")
            return None
        else:
            # Insert the user into the collection
            print(f"Trying to insert user document into DB : {self.db_name}, Collection :{self.collection_name}")
            result = self.collection.insert_one(user_document)
            print(f"DB LOG : Successfully inserted user document into DB : {self.db_name}, Collection :{self.collection_name} ")
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

        result = self.collection.update_one(
            {primary_key_name : primary_key_val},
            {"$set": updates},
            upsert=False
        )

        return {
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "acknowledged": result.acknowledged
        }

    def find_by_id(self, id_val: str, id_field: str) -> Optional[Dict]:
        """
        :param id_val : value of primary key to be searched
        :param id_field : primary key field name to be searched
        """
        if not id_field or not id_val: return None
        return self.collection.find_one({id_field: id_val.strip()})

    
    


