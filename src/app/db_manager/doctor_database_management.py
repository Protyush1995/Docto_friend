import csv
import os
import re
from datetime import datetime
from typing import Dict, Optional
from .db_operations import DatabaseOperations

# Base app directory (one level up from db_manager)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# CSV stored inside db_manager folder
CSV_PATH = os.path.join(BASE_DIR, "doctor_credentials_dataframe_database.csv")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LICENSE_RE = re.compile(r"^[A-Z0-9\-]{5,20}$", re.I)
PASS_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")

db = DatabaseOperations()


def validate_registration(data: Dict) -> Optional[str]:
    firstname = (data.get("firstname") or "").strip()
    lastname = (data.get("lastname") or "").strip()
    email = (data.get("email") or "").strip()
    license_no = (data.get("license") or "").strip()
    password = data.get("password") or ""

    #Field validity check
    if not firstname:
        return "First name is required"
    if not lastname:
        return "Last name is required"
    if not EMAIL_RE.match(email):
        return "Invalid email"
    if not LICENSE_RE.match(license_no):
        return "Invalid license number (5-20 alphanumeric/dash chars)"
    if not PASS_RE.match(password):
        return "Password must be at least 8 chars and include letters and numbers"
    
    # uniqueness checks against MongoDB for email and license_no
    if db.find_by_email(email):
        return "Email already registered"
    if db.find_by_license(license_no):
        return "License number already registered"
    
    return None

def _generate_doctor_id() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    rand = f"{os.urandom(2).hex()}"
    return f"D{ts}{rand}"

def _hash_password(password: str) -> str:
    # Placeholder: replace with bcrypt or passlib in production
    import hashlib
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def append_registration_record(data: Dict) -> Dict:
    """
    Validate and append registration record to CSV.
    Returns the saved record dict (without plaintext password).
    Raises ValueError on validation errors or Exception on IO errors.
    """
    print("Preparing NEW user record for database entry!!")
    err = validate_registration(data)
    if err:
        raise ValueError(err)


    doctor_id = _generate_doctor_id()
    password_hash = _hash_password(data["password"])

    record = {
        "doctor_id": doctor_id,
        "firstname": data["firstname"].strip(),
        "lastname": data["lastname"].strip(),
        "email": data["email"].strip().lower(),
        "license": data["license"].strip(),
        "password_hash": password_hash,
        "created_at": datetime.utcnow().isoformat(),
    }

    #inserting data to MongoDb database
    db.insert_user(user_document=record)

    return record


