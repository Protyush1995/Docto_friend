import json
import os
import re
import io
from io import BytesIO
from PIL import Image
import base64
import qrcode
from base64 import b64encode
from bson.binary import Binary
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Union
from .db_operations import DatabaseOperations


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

base = Path(__file__).parent
patient_env = (base / ".env.patients").resolve()
patient_db = DatabaseOperations(env_file=str(patient_env))

#TODO change host later as necessary
def _generate_patient_qr(patient_id: str, clinic_id: str, doctor_id: str, host: str = "http://192.168.29.115:5000") -> bytes:
    """
    Returns PNG bytes for a QR encoding a URL pointing to /clinic-booking
    with query params clinic_id and doctor_id.
    """
    # Build a compact URL/payload. Use absolute URL if you want (domain optional).
    # Example: /clinic-booking?clinic_id=CLINIC_ID_...&doctor_id=DOC123

    # TODO patient payload needs to redirect to generate prescription page for doctors only
    payload = f"{host}/patient-prescription-update?patient_id={patient_id}&clinic_id={clinic_id}&doctor_id={doctor_id}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
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

def _generate_patient_id() -> str:
    # numeric timestamp (UTC) + cryptographically random 8-digit number
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:-3]  # up to milliseconds, digits only
    rand_int = int.from_bytes(os.urandom(4), "big") % 10_000_000  # 0..9_999_999
    rand = f"{rand_int:07d}"  # fixed width 7 digits to reduce collision risk
    return f"PATIENT_ID_{ts}{rand}"

def append_patient_registration_record(data: Dict) -> Dict:
    """
    Validate and append registration record to CSV.
    Returns the saved record dict (without plaintext password).
    Raises ValueError on validation errors or Exception on IO errors.
    """
    print("Preparing NEW clinic record for database entry!!")
    #err = validate_registration(data)
    #if err:
    #    raise ValueError(err)


    patient_id = _generate_patient_id()
    qr_png_bytes = _generate_patient_qr(patient_id, data["clinic_id"].strip(), data["doctor_id"].strip())
    qr_png_data_uri = bytes_to_data_uri(png_bytes=qr_png_bytes)
    record = {
        "patient_id":patient_id,
        "clinic_id": data["clinic_id"].strip(),
        "doctor_id": data["doctor_id"].strip(),
        "patient_name": data["patient_name"].strip(),
        "age": data["age"],
        "sex": data["sex"].strip(),
        "occupation":"",
        "patient_address":"",
        "patient_mobile":data["patient_mobile"].strip(),
        "created_at": data["created_at"].strip(),
        "visit_day":data["visit_day"],
        "visit_date":data["visit_date"],
        "doctor_consultation_fees":data["clinic_fees"],
        "patient_qr_bytes":qr_png_bytes,
        "patient_qr_data_uri":qr_png_data_uri,
    }

    #inserting data to MongoDb database
    #response = patient_db.insert_record(user_document=record)
    #response["patient_qr_data_uri"] = qr_png_data_uri

    result = patient_db.insert_record(user_document=record)  # returns InsertOneResult or ObjectId
    # if insert returns InsertOneResult:
    inserted_id = getattr(result, "inserted_id", result)  # handles both cases
    record_copy = dict(record)
    record_copy["_id"] = inserted_id
    record_copy["patient_qr_data_uri"] = qr_png_data_uri
    return record_copy


def update_patient_profile(data: Dict) -> Dict:
    #updating profile data of MongoDb database
    success = patient_db.update_record (primary_key_name="patient_id",primary_key_val=data["patient_id"],updates=data)
    response = {"success":success["acknowledged"],"clinic_id":data["clinic_id"]}
    print("PATIENT DB MANAGEMENT LOG : Message returned by Mongo for clinic profile update...........")
    print(json.dumps(success))
    print("PATIENT DB MANAGEMENT LOG : Response constructed for clinic profile update...........")
    print(json.dumps(response))
    print("PATIENT DB MANAGEMENT LOG : Returning constructed response...........")
    return response

def get_clinic_by_doctor_id(doctor_id:str) -> Dict:
    doctor_data = patient_db.find_by_id(id_val=doctor_id,id_field="doctor_id")
    return doctor_data

def get_clinic_by_clinic_id(clinic_id:str) -> Dict:
    clinic_data = patient_db.find_by_id(id_val=clinic_id,id_field="clinic_id")
    return clinic_data