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
clinic_env = (base / ".env.clinics").resolve()
clinic_db = DatabaseOperations(env_file=str(clinic_env))

def _generate_clinic_qr(clinic_id: str, doctor_id: str) -> bytes:
    """
    Returns PNG bytes for a QR encoding a URL pointing to /clinic-booking
    with query params clinic_id and doctor_id.
    """
    # Build a compact URL/payload. Use absolute URL if you want (domain optional).
    # Example: /clinic-booking?clinic_id=CLINIC_ID_...&doctor_id=DOC123
    payload = f"/clinic-booking?clinic_id={clinic_id}&doctor_id={doctor_id}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    # Get the current file's directory.
    current_directory = os.path.dirname(os.path.abspath(__file__))
    
    # Define the file path (you can specify a filename as needed).
    file_path = os.path.join(current_directory, f"clinic_qr_{clinic_id}_{doctor_id}.png")
    
    # Save the image to the specified file path.
    img.save(file_path)

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


def _generate_clinic_id() -> str:
    # numeric timestamp (UTC) + cryptographically random 8-digit number
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:-3]  # up to milliseconds, digits only
    rand_int = int.from_bytes(os.urandom(4), "big") % 10_000_000  # 0..9_999_999
    rand = f"{rand_int:07d}"  # fixed width 7 digits to reduce collision risk
    return f"CLINIC_ID_{ts}{rand}"

def append_clinic_registration_record(data: Dict) -> Dict:
    """
    Validate and append registration record to CSV.
    Returns the saved record dict (without plaintext password).
    Raises ValueError on validation errors or Exception on IO errors.
    """
    print("Preparing NEW clinic record for database entry!!")
    #err = validate_registration(data)
    #if err:
    #    raise ValueError(err)


    clinic_id = _generate_clinic_id()
    qr_png_bytes = _generate_clinic_qr(clinic_id, data["doctor_id"].strip())
    qr_png_data_uri = bytes_to_data_uri(png_bytes=qr_png_bytes)
    record = {
        "clinic_id": clinic_id,
        "doctor_id": data["doctor_id"].strip(),
        "clinicname": data["clinic_name"].strip(),
        "email": data["clinic_email"].strip(),
        "clinic_address":data["clinic_address"],
        "primary_contact_number":data["clinic_contact"].strip(),
        "secondary_contact_number":data["clinic_contact_alternative"].strip(),
        "created_at": datetime.utcnow().date().isoformat(),
        "services_offered":"",
        "visit_schedule":data["visit_schedule"],
        "doctor_consultation_fees":data["clinic_fees"],
        "clinic_qr_bytes":qr_png_bytes,
        "clinic_qr_data_uri":qr_png_data_uri,
    }

    #inserting data to MongoDb database
    response = clinic_db.insert_record(user_document=record)

    return response

def get_clinic_by_doctor_id(doctor_id:str) -> Dict:
    doctor_data = clinic_db.find_by_id(id_val=doctor_id,id_field="doctor_id")
    return doctor_data