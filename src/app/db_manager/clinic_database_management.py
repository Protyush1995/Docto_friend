import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from .db_operations import DatabaseOperations


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

base = Path(__file__).parent
clinic_env = (base / ".env.clinics").resolve()
clinic_db = DatabaseOperations(env_file=str(clinic_env))

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
    #password_hash = _hash_password(data["password"])

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
    }

    #inserting data to MongoDb database
    response = clinic_db.insert_record(user_document=record)

    return response

def get_clinic_by_doctor_id(doctor_id:str) -> Dict:
    doctor_data = clinic_db.find_by_id(id_val=doctor_id,id_field="doctor_id")
    del doctor_data["_id"] #removing mongodb ObjectId
    return doctor_data