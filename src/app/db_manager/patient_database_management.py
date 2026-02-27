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
# Add near top of your module
MAX_ID_ATTEMPTS = 10

def _token_exists(token: str) -> bool:
    match_list = patient_db.find_by_id(id_val=token, id_field="token_number")
    if len(match_list) == 0 :
        token_exists =  False
    else: token_exists = True
    print(f"PATIENT DB LOG :: Token no {token} exists already in patient collection:: {token_exists}")
    return token_exists

def _generate_patient_id_and_token() -> (str,str):
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:-3]  # up to milliseconds
    for _ in range(MAX_ID_ATTEMPTS):
        rand_int = int.from_bytes(os.urandom(4), "big") % 10_000_000  # int 0..9_999_999
        rand_str = f"{rand_int:07d}"  # keep as int
        # check token uniqueness in DB
        print(f"PATIENT DB LOG :: Checking token in patient collection:: attempt {_} ")
        if not _token_exists(rand_str):
            print(f"PATIENT DB LOG :: Patient Id {f"PATIENT_ID_{ts}{rand_str}"} and token number {rand_str} is now being alloted to patient")
            return f"PATIENT_ID_{ts}{rand_str}" , rand_str
        
    raise RuntimeError(f"Could not generate unique token after {MAX_ID_ATTEMPTS} attempts")

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


    patient_id ,patient_token = _generate_patient_id_and_token()
    serial_number = get_patient_serial_number(doctor_id=data["doctor_id"].strip(),visit_date=data["visit_date"])

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
        "token_number":patient_token,
        "serial_number":serial_number,
        "appointment_week":data["appointment_week"],
        "appointment_year":data["appointment_year"],
        "checked_in":data["checked_in"]
    }

    result = patient_db.insert_record(user_document=record)  # returns InsertOneResult or ObjectId
    inserted_id = getattr(result, "inserted_id", result)
    record_copy = dict(record)
    record_copy["_id"] = inserted_id

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

def get_patient_by_doctor_id(doctor_id:str) -> Dict:
    patient_data = patient_db.find_by_id(id_val=doctor_id,id_field="doctor_id")
    return patient_data

def get_patient_by_token_number(token_number:int) -> Dict:
    patient_data = patient_db.find_by_id(id_val=token_number,id_field="token_number")
    return patient_data

def get_patient_serial_number(doctor_id:str,visit_date:str) -> Dict:
    patient_serial_list = patient_db.find_by_two_fields(field1="doctor_id",val1=doctor_id,field2="visit_date",val2=visit_date)
    if patient_serial_list is None:
        raise ValueError(f"PATIENT DB LOG :: Could not generate serial number invalid value passed to find_by_two_fields function")

    length = len(patient_serial_list)
    if length > 0:
        serial_number = length+1
    elif length == 0:
        serial_number = 1
    print(f"PATIENT DB LOG :: Alloting serial number:{serial_number} to patient")
    return serial_number