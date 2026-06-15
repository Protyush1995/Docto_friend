import json
import os
import re
from io import BytesIO
from PIL import Image
from pathlib import Path
import base64
import qrcode
from base64 import b64encode
from bson.binary import Binary
from datetime import datetime
from typing import Dict, Optional, Union
from .db_operations import DatabaseOperations

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LICENSE_RE = re.compile(r"^[A-Z0-9\-]{5,20}$", re.I)
PASS_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")

db = DatabaseOperations()

#TODO change host later as necessary
def _generate_doctor_qr(USER: Optional[str] ,REPO: str ="Docto_friend") -> Optional[bytes]:
    """
    Returns PNG bytes for a QR encoding a URL pointing to /clinic-booking
    with query params clinic_id and doctor_id.
    """
    # Build a compact URL/payload. Use absolute URL if you want (domain optional).
    
    if not USER:  # explicit check for missing/empty user
        return None
    
    payload = f"https://{USER}.github.io/{REPO}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")

    return buf.getvalue()

# Helper: bytes -> PIL.Image
def bytes_to_pil_image(png_bytes: bytes) -> Image.Image:
    return Image.open(BytesIO(png_bytes))

# Helper: bytes -> base64 data URI for embedding in HTML
def bytes_to_data_uri(png_bytes: bytes) -> str:
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"

def base64_string_to_data_uri(b64_input: Union[str, bytes], mime: Optional[str] = None) -> str:
    """
    Convert a stringified base64 (or bytes) to a data URI.
    - b64_input: base64 string (may already be a data URI) or raw bytes.
    - mime: optional MIME type like 'image/png' or 'image/jpeg'. If omitted and b64_input is a data URI,
            the function preserves its MIME; otherwise defaults to 'application/octet-stream'.
    Returns a data URI string: "data:{mime};base64,{b64}"
    """
    # If bytes were passed, treat as raw bytes -> encode to base64
    if isinstance(b64_input, (bytes, bytearray)):
        b64 = base64.b64encode(b64_input).decode('ascii')
        mime = mime or 'application/octet-stream'
        return f"data:{mime};base64,{b64}"

    s = b64_input.strip()
    # If already a data URI, normalize and return
    if s.startswith('data:') and ';base64,' in s:
        return s

    # If it looks like a data URI but missing "data:" prefix (rare), try to split
    if ';base64,' in s and not s.startswith('data:'):
        # assume it already contains mime before ;base64,
        return f"data:{s}"

    # Otherwise s is expected to be raw base64 (no prefix). Validate/clean whitespace.
    # Remove any whitespace/newlines that may have been introduced.
    cleaned = ''.join(s.split())
    # Optionally validate by attempting a decode (will raise if invalid)
    try:
        _ = base64.b64decode(cleaned, validate=True)
    except Exception:
        # If invalid base64, raise a clear error
        raise ValueError('Input is not valid base64 or data URI')

    mime = mime or 'application/octet-stream'
    return f"data:{mime};base64,{cleaned}"

def validate_registration(data: Dict) -> Optional[str]:
    firstname = (data.get("firstname") or "").strip()
    lastname = (data.get("lastname") or "").strip()
    email = (data.get("email") or "").strip()
    license_no = (data.get("license") or "").strip()
    password = data.get("password") or ""
    github_user_name = (data.get("github_user_name") or "").strip()

    #Field validity check
    if not firstname:
        return "First name is required"
    if not lastname:
        return "Last name is required"
    if not github_user_name:
        return "Github user name is required"
    if not EMAIL_RE.match(email):
        return "Invalid email"
    if not LICENSE_RE.match(license_no):
        return "Invalid license number (5-20 alphanumeric/dash chars)"
    if not PASS_RE.match(password):
        return "Password must be at least 8 chars and include letters and numbers"
    
    # uniqueness checks against MongoDB for email and license_no
    if db.find_by_id(id_val=email,id_field="email"):
        return "Email already registered"
    if db.find_by_id(id_val=license_no,id_field="license"):
        return "License number already registered"
    
    return None

def _generate_doctor_id() -> str:
    # numeric timestamp (UTC) + cryptographically random 8-digit number
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:-3]  # up to milliseconds, digits only
    rand_int = int.from_bytes(os.urandom(4), "big") % 10_000_000  # 0..9_999_999
    rand = f"{rand_int:07d}"  # fixed width 7 digits to reduce collision risk
    return f"DOC_ID_{ts}{rand}"

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
    print("DOCTOR DB MANAGEMENT LOG : Preparing NEW user record for database entry!!")
    err = validate_registration(data)
    if err:
        raise ValueError(err)

    # Defensive extraction: ensure a plain string (not a tuple/list)
    raw_user = data.get("github_user_name", "") or ""
    if isinstance(raw_user, (list, tuple)):
        raw_user = raw_user[0] if raw_user else ""

    github_user_name = str(raw_user).strip()

    print(f"GITHUB USER NAME :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::{repr(github_user_name)}")
    print(f"GITHUB USER NAME :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::{github_user_name}")

    doctor_id = _generate_doctor_id()
    qr_png_bytes = _generate_doctor_qr(USER=github_user_name)
    if not qr_png_bytes:
        qr_png_data_uri = None
    else : qr_png_data_uri = bytes_to_data_uri(png_bytes=qr_png_bytes)
    password_hash = _hash_password(data["password"])

    record = {
        "doctor_id": doctor_id,
        "firstname": data["firstname"].strip(),
        "lastname": data["lastname"].strip(),
        "github_user_name": github_user_name,
        "email": data["email"].strip().lower(),
        "license": data["license"].strip(),
        "permanent_address":"",
        "primary_contact_number":data["mobile"].strip(),
        "secondary_contact_number":0,
        "password_hash": password_hash,
        "created_at": datetime.utcnow().date().isoformat(),
        "qualifications":"",
        "expertise":"",
        "practising_or_fellowship":"",
        "achievements":"",
        "years_of_experience":0,
        "default_fees":500, 
        "doctor_qr_uri":qr_png_data_uri
    }

    #inserting data to MongoDb database
    db.insert_record(user_document=record)

    return record

def update_doctor_profile(data: Dict) -> Dict:

    #updating profile data of MongoDb database
    print(data)
    if "image_data" in data :
        profile_pic_uri = base64_string_to_data_uri(data["image_data"],data['image_mime'])
        data["profile_pic_uri"] = profile_pic_uri

    success = db.update_record (primary_key_name="doctor_id",primary_key_val=data["doctor_id"],updates=data)
    response = {"success":success["acknowledged"],"doctor_id":data["doctor_id"]}
    print("DOCTOR DB MANAGEMENT LOG : Message returned by Mongo for profile update...........")
    print(json.dumps(success))
    print("DOCTOR DB MANAGEMENT LOG : Response constructed for profile update...........")
    print(json.dumps(response))
    print("DOCTOR DB MANAGEMENT LOG : Returning constructed response...........")
    return response

def get_doctor_by_id(doctor_id:str) -> Dict:
    doctor_data = db.find_by_id(id_val=doctor_id,id_field="doctor_id")
    return doctor_data

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
        rec = db.find_by_id(id_val=ident,id_field="email")
    else:
        rec = db.find_by_id(id_val=ident,id_field="license")

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

