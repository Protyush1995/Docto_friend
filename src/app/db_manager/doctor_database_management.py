import csv
import os
import re
from datetime import datetime
from typing import Dict, Optional
from .db_operations import DatabaseOperations

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
    # numeric timestamp (UTC) + cryptographically random 8-digit number
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:-3]  # up to milliseconds, digits only
    rand_int = int.from_bytes(os.urandom(4), "big") % 10_000_000  # 0..9_999_999
    rand = f"{rand_int:07d}"  # fixed width 7 digits to reduce collision risk
    return f"DOC_ID_{ts}{rand}"



def _generate_clinic_id(clinic_name: str) -> str:
    # numeric timestamp (UTC) + cryptographically random 8-digit number
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:-3]  # up to milliseconds, digits only
    rand_int = int.from_bytes(os.urandom(4), "big") % 10_000_000  # 0..9_999_999
    rand = f"{rand_int:07d}"  # fixed width 7 digits to reduce collision risk
    return f"CLINIC_ID_{clinic_name}_{rand}"



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
        "home_address":"",
        "primary_contact_number":data["mobile"].strip(),
        "secondary_contact_number":0,
        "password_hash": password_hash,
        "created_at": datetime.utcnow().date().isoformat(),
        "qualifications":"",
        "expertise":"",
        "practising_or_fellowship":"",
        "achievements":"",
    }

    #inserting data to MongoDb database
    db.insert_user(user_document=record)

    return record

def verify_password(plain: str, stored_hash: str) -> bool:
    if not plain or not stored_hash:
        return False
    return _hash_password(plain) == stored_hash

def authenticate_identifier(identifier: str, password: str) -> Dict:
    """
    identifier: email or license string
    password: plaintext password provided by user

    Returns a dict: { "success": bool, "error": str (if any), "user": sanitized_record (if success) }
    """
    ident = (identifier or "").strip()
    if not ident or not password:
        return {"success": False, "error": "MISSING CREDENNTIALS!!!"}

    # determine lookup
    if EMAIL_RE.match(ident):
        rec = db.find_by_email(ident)
    else:
        rec = db.find_by_license(ident)

    if not rec:
        return {"success": False, "error": "Error !! NO USER FOUND!!"}

    #Checking with hashed password
    stored_hash = rec.get("password_hash","")
    if stored_hash == "" :  return {"success": False, "error": "Error !! CONTACT ADMNISTRATOR !! Password Absent!!"}
    if verify_password(password, stored_hash):
        # sanitize: do not return plaintext password or hash
        user = {k: v for k, v in rec.items() if k not in ("password", "password_hash","_id")}
        return {"success": True, "user": user}
    
    return {"success": False, "error": "invalid_credentials"}

