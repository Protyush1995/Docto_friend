import json
import os
import re
from datetime import datetime
from typing import Dict, Optional
from .db_operations import DatabaseOperations


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LICENSE_RE = re.compile(r"^[A-Z0-9\-]{5,20}$", re.I)
PASS_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")

clinic_db = DatabaseOperations(env_file="C:\Users\Protyush\Desktop\docto_friend\Docto_friend\src\app\db_manager\.env.clinics")

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
        "clinicname": data["clinicName"].strip(),
        "email": data["clinicemail"].strip(),
        "clinic_address":"",
        "primary_contact_number":data["clinic_contact"].strip(),
        "secondary_contact_number":data["clinic_contact_alternative"].strip(),
        "created_at": datetime.utcnow().date().isoformat(),
        "services_offered":"",
        "visit_schedule":data["schedule"],
        "doctor_consultation_fees":data["clinicFees"],
    }

    #inserting data to MongoDb database
    response = clinic_db.insert_record(user_document=record)

    return response


def get_clinic_by_doctor_id(doctor_id:str) -> Dict:
    doctor_data = clinic_db.find_by_id(id_val=doctor_id,id_field="doctor_id")
    del doctor_data["_id"] #removing mongodb ObjectId
    return doctor_data