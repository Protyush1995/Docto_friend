import os
import csv
import qrcode
import json
import uuid
import base64
from datetime import datetime
from urllib.parse import quote_plus
from io import BytesIO

# Base app directory (one level up from db_manager)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Save QR images under app's static folder so Flask can serve them
QR_DIR = os.path.join(BASE_DIR, "static", "qr")
os.makedirs(QR_DIR, exist_ok=True)

# CSV stored inside db_manager folder
CSV_PATH = os.path.join(os.path.dirname(__file__), "doctor_db_dataframe.csv")

# Added fields:
# - doctor_first_name, doctor_last_name
# - doctor_id (generated): DOCID_<DoctorLastName>_<UniqueNumberPerDoctor>
# - clinic_id (generated): CLINID_<ClinicName>_<UniqueNumberPerClinic>
# - DOCLID (generated): DOCLID_<ClinicName>_<UniqueNumberPerClinic>_<DoctorLastName>_<UniqueNumberPerDoctor>
# - qr_image_base64 (stores PNG binary as base64)
CSV_FIELDS = [
    "doctor_id",
    "doctor_first_name",
    "doctor_last_name",
    "doctor_qualifications",
    "clinic_id",
    "clinic_name",
    "clinic_fees",
    "clinic_address",
    "clinic_contact",
    "doctor_visit_days",
    "DOCLID",
    "qr_filename",
    "qr_image_base64",
    "created_at",
]

# Helper files to persist simple counters per clinic/doctor
COUNTER_DIR = os.path.join(os.path.dirname(__file__), "counters")
os.makedirs(COUNTER_DIR, exist_ok=True)
DOCTOR_COUNTER_PATH = os.path.join(COUNTER_DIR, "doctor_counter.csv")
CLINIC_COUNTER_PATH = os.path.join(COUNTER_DIR, "clinic_counter.csv")

def _ensure_csv():
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()

def _load_counter(path):
    d = {}
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    d[row[0]] = int(row[1])
    return d

def _save_counter(path, d):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for k, v in d.items():
            writer.writerow([k, v])

def _increment_counter_for(key: str, path: str):
    d = _load_counter(path)
    v = d.get(key, 0) + 1
    d[key] = v
    _save_counter(path, d)
    return v

def _generate_qr_payload(fields: dict) -> str:
    payload = {
        "doctor_id": fields.get("doctor_id"),
        "doctor_first_name": fields.get("doctor_first_name"),
        "doctor_last_name": fields.get("doctor_last_name"),
        "doctor_qualifications": fields.get("doctor_qualifications"),
        "clinic_id": fields.get("clinic_id"),
        "clinic_name": fields.get("clinic_name"),
        "clinic_fees": fields.get("clinic_fees"),
        "clinic_address": fields.get("clinic_address"),
        "clinic_contact": fields.get("clinic_contact"),
        "doctor_visit_days": fields.get("doctor_visit_days"),
    }
    return json.dumps(payload, ensure_ascii=False)

def _save_qr_image_to_disk(img, filename: str) -> None:
    path = os.path.join(QR_DIR, filename)
    img.save(path, format="PNG")

def _make_unique_filename() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"doctor_qr_{ts}_{uuid.uuid4().hex[:8]}.png"

def _doctor_exists(doctor_id: str) -> str:
    if not os.path.exists(CSV_PATH):
        return ""
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if (r.get("doctor_id") or "") == doctor_id:
                return r.get("qr_filename", "") or ""
    return ""

def _create_qr_image_bytes(data: str) -> bytes:
    img = qrcode.make(data)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def _safe_id_component(s: str) -> str:
    # keep alnum and underscores only, collapse spaces to underscore
    return "".join(c for c in (s or "") if c.isalnum() or c in " _-").strip().replace(" ", "_")

def append_doctor_record(fields: dict) -> str:
    """
    Existing behavior preserved. Changes:
    - Split doctor_name into first/last from fields['doctor_name'] input.
    - Generate doctor_id and clinic_id automatically and DOCLID.
    - Store new fields in CSV. Other functionality unchanged.
    """
    _ensure_csv()
    print("From form to backend:#################################################")
    for key, value in fields.items():
        print(f"{key}: {value}")
    # Parse and validate provided name (we still accept a single 'doctor_name' input from the form)
    doctor_first = (fields.get("doctor_first_name") or "").strip()
    if not doctor_first:
        raise ValueError("doctor_first_name is required")
    doctor_last = (fields.get("doctor_last_name") or "").strip()
    if not doctor_last:
        raise ValueError("doctor_last_name is required")
    

    # Generate clinic_name canonical and clinic counter
    clinic_name_raw = (fields.get("clinic_name") or "").strip() or "Clinic"
    clinic_key = _safe_id_component(clinic_name_raw).upper()
    clinic_counter = _increment_counter_for(clinic_key, CLINIC_COUNTER_PATH)
    # Clinic ID format: CLINID_<ClinicName>_<UniqueNumberPerClinic>
    clinic_id_generated = f"CLINID_{clinic_key}_{clinic_counter}"

    # Generate doctor id using last name and doctor counter (unique per doctor last name)
    doctor_key = _safe_id_component(doctor_last).upper()
    doctor_counter = _increment_counter_for(doctor_key, DOCTOR_COUNTER_PATH)
    # Doctor ID format: DOCID_<DoctorLastName>_<UniqueNumberPerDoctor>
    doctor_id_generated = f"DOCID_{doctor_key}_{doctor_counter}"

    # DOCLID format: DOCLID_<ClinicName>_<UniqueNumberPerClinic>_<DoctorLastName>_<UniqueNumberPerDoctor>
    doclid = f"DOCLID_{clinic_key}_{clinic_counter}_{doctor_key}_{doctor_counter}"

    # Check if record with same doctor_id exists; preserve previous behavior (if exists return existing qr)
    existing_qr = _doctor_exists(doctor_id_generated)
    if existing_qr:
        return existing_qr

    # validate clinic_fees if provided
    fees = (fields.get("clinic_fees") or "").strip()
    if fees:
        try:
            f = float(fees)
            if f < 0:
                raise ValueError("clinic_fees must be non-negative")
        except ValueError:
            raise ValueError("clinic_fees must be a valid non-negative number")

    # Create QR filename
    qr_filename = _make_unique_filename()

    # Build JSON payload using the helper so QR contains the dictionary info
    qr_payload = _generate_qr_payload({
        "doctor_id": doctor_id_generated,
        "doctor_first_name": doctor_first,
        "doctor_last_name": doctor_last,
        "doctor_qualifications": fields.get("doctor_qualifications", ""),
        "clinic_id": clinic_id_generated,
        "clinic_name": clinic_name_raw,
        "clinic_fees": fields.get("clinic_fees", ""),
        "clinic_address": fields.get("clinic_address", ""),
        "clinic_contact": fields.get("clinic_contact", ""),
        "doctor_visit_days": fields.get("doctor_visit_days", ""),
    })

    # Create QR image bytes from payload and save disk copy
    png_bytes = _create_qr_image_bytes(qr_payload)
    from PIL import Image
    img_buf = BytesIO(png_bytes)
    img = Image.open(img_buf)
    _save_qr_image_to_disk(img, qr_filename)


    # Encode PNG bytes as base64 for CSV storage
    qr_b64 = base64.b64encode(png_bytes).decode("ascii")

    # Prepare CSV record and append (includes generated ids and DOCLID)
    record = {
        "doctor_id": doctor_id_generated,
        "doctor_first_name": doctor_first,
        "doctor_last_name": doctor_last,
        "doctor_qualifications": fields.get("doctor_qualifications", ""),
        "clinic_id": clinic_id_generated,
        "clinic_name": clinic_name_raw,
        "clinic_fees": fields.get("clinic_fees", ""),
        "clinic_address": fields.get("clinic_address", ""),
        "clinic_contact": fields.get("clinic_contact", ""),
        "doctor_visit_days": fields.get("doctor_visit_days", ""),
        "DOCLID": doclid,
        "qr_filename": qr_filename,
        "qr_image_base64": qr_b64,
        "created_at": datetime.utcnow().isoformat(),
    }
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writerow(record)
    print(qr_filename)
    return qr_filename