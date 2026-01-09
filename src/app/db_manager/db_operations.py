from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
import hashlib
from dotenv import load_dotenv
from typing import Dict, Optional
import os,json
from pathlib import Path
from datetime import datetime

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

    def create_collection(self,collection):
        # Ensure the collection exists
        if collection not in self.db.list_collection_names():
            self.db.create_collection(collection)
        return collection

    def insert_user(self, user_document: Dict):
        # Create a user document
        if not user_document:
            print ("!!WARNING!! Empty user data!! nothing to enter in database!!")
            return None
        else:
            # Insert the user into the collection
            result = self.collection.insert_one(user_document)
            return result.inserted_id  # Return the new user's ID
        
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

    @staticmethod
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
    







class ClinicDB:
    def __init__(self, env_file=None):
        """
        :param env_file: Path or str to .env file. If None, defaults to sibling .env.doctors.
        """
        
        # resolve env_file to a Path before using .is_file()
        if env_file is None:
            env_path = Path(__file__).parent / ".env.clinics"
        else:
            env_path = Path(env_file)

        if env_path.is_file():
            load_dotenv(env_path)
            print(f"Loaded environment variables from: {env_path}")
        else:
            raise RuntimeError(f".env file not found: {env_path}")

        client_url = os.getenv("CLINIC_MONGO_URL")
        db_name = os.getenv("CLINIC_DB_NAME")
        collection_name = os.getenv("CLINIC_COLLECTION_NAME")
        
        missing = [n for n, v in (("CLINIC_MONGO_URL", client_url),
                                ("CLINIC_DB_NAME", db_name),
                                ("CLINIC_COLLECTION_NAME", collection_name)) if not v]
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

    def create_collection(self,collection):
        # Ensure the collection exists
        if collection not in self.db.list_collection_names():
            self.db.create_collection(collection)
        return collection


    def add_clinic(self, doctor_id: str, clinic_data: dict):
        """
        Insert a new clinic for a doctor.
        clinic_data should already contain:
        - clinic_name
        - address
        - fees
        - contact
        - schedule
        """
        print("******************************************************************************************")
        print("Preparing NEW clinic record for database entry!!")
        print(self.collection_name)
        clinic_document = {
            "doctor_id": doctor_id,
            "clinic_id": clinic_data["clinic_id"],
            "clinic_name": clinic_data["clinic_name"],
            "clinic_contact": clinic_data["clinic_contact"],
            "clinic_fees": clinic_data["clinic_fees"],
            "address": clinic_data["address"],
            "schedule": clinic_data["schedule"],
            "created_at": datetime.utcnow().date().isoformat(),
            "updated_at": datetime.utcnow().date().isoformat()
        }
        print(clinic_document)      
        result = self.collection.insert_one(clinic_document)
        return str(result.inserted_id)
