import csv
import os
import re
from datetime import datetime
from typing import Dict, Optional

# Base directory (db_manager package directory)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# CSV stored inside "Doctor credentials database" folder under db_manager
DB_DIR = os.path.join(BASE_DIR, "Doctor credentials database")
CSV_PATH = os.path.join(DB_DIR, "doctor_credentials_dataframe_database.csv")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LICENSE_RE = re.compile(r"^[A-Z0-9\-]{5,20}$", re.I)
PASS_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")

# CSV headers for registration records — plaintext password included (insecure)
HEADERS = [
    "doctor_id",
    "firstname",
    "lastname",
    "email",
    "license",
    "password",         # plaintext (insecure) — confirmed by you
    "password_hash",
    "created_at",
    "verified",
]

def ensure_csv():
    os.makedirs(DB_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writeheader()

def validate_registration(data: Dict) -> Optional[str]:
    firstname = (data.get("firstname") or "").strip()
    lastname = (data.get("lastname") or "").strip()
    email = (data.get("email") or "").strip()
    license_no = (data.get("license") or "").strip()
    password = data.get("password") or ""

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
    # check uniqueness
    ensure_csv()
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("email","").lower() == email.lower():
                return "Email already registered"
            if r.get("license","").lower() == license_no.lower():
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
    Returns the saved record dict.
    Raises ValueError on validation errors or Exception on IO errors.
    """
    err = validate_registration(data)
    if err:
        raise ValueError(err)

    ensure_csv()
    doctor_id = _generate_doctor_id()
    password_plain = data["password"]
    password_hash = _hash_password(password_plain)

    record = {
        "doctor_id": doctor_id,
        "firstname": data["firstname"].strip(),
        "lastname": data["lastname"].strip(),
        "email": data["email"].strip().lower(),
        "license": data["license"].strip(),
        "password": password_plain,       # stored plaintext (you confirmed)
        "password_hash": password_hash,
        "created_at": datetime.utcnow().isoformat(),
        "verified": "false",
    }

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writerow(record)

    # Do not return plaintext in API responses
    rec_copy = record.copy()
    rec_copy.pop("password", None)
    return rec_copy

def find_by_email(email: str) -> Optional[Dict]:
    ensure_csv()
    email = (email or "").strip().lower()
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("email","").lower() == email:
                return r
    return None

def find_by_license(license_no: str) -> Optional[Dict]:
    ensure_csv()
    license_no = (license_no or "").strip().lower()
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("license","").lower() == license_no:
                return r
    return None

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
        return {"success": False, "error": "missing_credentials"}

    # determine lookup
    if EMAIL_RE.match(ident):
        rec = find_by_email(ident)
    else:
        rec = find_by_license(ident)

    if not rec:
        return {"success": False, "error": "not_found"}

    stored_hash = rec.get("password_hash") or ""
    if verify_password(password, stored_hash):
        # sanitize: do not return plaintext password or hash
        user = {k: v for k, v in rec.items() if k not in ("password", "password_hash")}
        return {"success": True, "user": user}
    # optional: if you want to allow plaintext comparison (since file stores it)
    stored_plain = rec.get("password")
    if stored_plain and stored_plain == password:
        user = {k: v for k, v in rec.items() if k not in ("password", "password_hash")}
        return {"success": True, "user": user}

    return {"success": False, "error": "invalid_credentials"}
