import csv
import os
import re
from datetime import datetime
from typing import Dict, Optional

# Base app directory (one level up from db_manager)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# CSV stored inside db_manager folder
CSV_PATH = os.path.join(BASE_DIR, "doctor_db_dataframe.csv")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LICENSE_RE = re.compile(r"^[A-Z0-9\-]{5,20}$", re.I)
PASS_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")

# CSV headers for registration records
HEADERS = [
    "doctor_id",        # generated unique id
    "fullname",
    "email",
    "license",
    "password_hash",    # store hashed password (for demo we store placeholder)
    "created_at",
    "verified",         # false until email verification
]

def ensure_csv():
    os.makedirs(BASE_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writeheader()

def validate_registration(data: Dict) -> Optional[str]:
    name = (data.get("fullname") or "").strip()
    email = (data.get("email") or "").strip()
    license_no = (data.get("license") or "").strip()
    password = data.get("password") or ""

    if not name:
        return "Full name is required"
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
    Returns the saved record dict (without plaintext password).
    Raises ValueError on validation errors or Exception on IO errors.
    """
    err = validate_registration(data)
    if err:
        raise ValueError(err)

    ensure_csv()
    doctor_id = _generate_doctor_id()
    password_hash = _hash_password(data["password"])

    record = {
        "doctor_id": doctor_id,
        "fullname": data["fullname"].strip(),
        "email": data["email"].strip().lower(),
        "license": data["license"].strip(),
        "password_hash": password_hash,
        "created_at": datetime.utcnow().isoformat(),
        "verified": "false",
    }

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writerow(record)

    return record

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
