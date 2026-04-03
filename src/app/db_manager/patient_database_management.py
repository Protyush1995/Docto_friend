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
from datetime import datetime, date, time, timedelta, timezone
import zoneinfo

def get_iso_week(dt):
    """
    Compute ISO year/week using the date components in IST.
    Accepts date or datetime; uses IST-local date (year/month/day) to construct
    an IST-midnight datetime and then follows ISO week rules.
    Returns {'year': int, 'week': int}.
    """
    # If datetime, convert to IST then take date; if date, use directly
    if isinstance(dt, datetime):
        dt_ist = dt.astimezone(IST)
        d = dt_ist.date()
    else:
        d = dt  # assume date

    # Construct IST-midnight for that local date
    d_ist_mid = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=IST)

    # ISO weekday: Mon=1 .. Sun=7
    day_num = d_ist_mid.isoweekday()

    # Move to Thursday of this week (IST)
    d_thu_ist = d_ist_mid + timedelta(days=(4 - day_num))

    # Jan 1 of that ISO-year at IST midnight
    year_start_ist = datetime(d_thu_ist.year, 1, 1, 0, 0, 0, tzinfo=IST)

    days_diff = (d_thu_ist - year_start_ist).days
    week_no = (days_diff + 1 + 6) // 7

    return {'year': d_thu_ist.year, 'week': week_no}


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

base = Path(__file__).parent
patient_env = (base / ".env.patients").resolve()
patient_db = DatabaseOperations(env_file=str(patient_env))
# Add near top of your module
MAX_ID_ATTEMPTS = 10

IST = zoneinfo.ZoneInfo("Asia/Kolkata")

DATE_TODAY = datetime.now(IST).date()
week_year = get_iso_week(DATE_TODAY)
CURRENT_WEEK = week_year["week"]
CURRENT_YEAR = week_year["year"]

def parse_iso_z(s: str) -> datetime:
    """
    Accepts ISO strings like "2026-03-02T18:30:00.000Z" (UTC) or with offset.
    Returns an aware datetime converted to IST (Asia/Kolkata).
    """
    # Normalize trailing Z to +00:00 so fromisoformat accepts it
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    dt = datetime.fromisoformat(s)  # may be offset-aware
    # Convert to IST
    if dt.tzinfo is None:
        # assume naive input is UTC then convert
        dt = dt.replace(tzinfo=timezone.utc)

    IST_date = dt.astimezone(IST)
    print(f"PATIENT DB LOG :: Printing IST date = {IST_date}, from received date {s} _________________")
    return IST_date

def get_iso_week(dt):
    """
    Compute ISO year/week using the date components in IST.
    Accepts date or datetime; uses IST-local date (year/month/day) to construct
    an IST-midnight datetime and then follows ISO week rules.
    Returns {'year': int, 'week': int}.
    """
    # If datetime, convert to IST then take date; if date, use directly
    if isinstance(dt, datetime):
        dt_ist = dt.astimezone(IST)
        d = dt_ist.date()
    else:
        d = dt  # assume date

    # Construct IST-midnight for that local date
    d_ist_mid = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=IST)

    # ISO weekday: Mon=1 .. Sun=7
    day_num = d_ist_mid.isoweekday()

    # Move to Thursday of this week (IST)
    d_thu_ist = d_ist_mid + timedelta(days=(4 - day_num))

    # Jan 1 of that ISO-year at IST midnight
    year_start_ist = datetime(d_thu_ist.year, 1, 1, 0, 0, 0, tzinfo=IST)

    days_diff = (d_thu_ist - year_start_ist).days
    week_no = (days_diff + 1 + 6) // 7

    return {'year': d_thu_ist.year, 'week': week_no}

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
            print(f"PATIENT DB LOG :: Patient Id: {f"PATIENT_ID_{ts}{rand_str}"} , uTAN: {rand_str} is now being alloted to patient")
            return f"PATIENT_ID_{ts}{rand_str}" , rand_str
        
    raise RuntimeError(f"Could not generate uTAN after {MAX_ID_ATTEMPTS} attempts")

def append_patient_registration_record(data: Dict) -> Dict:
    """
    Validate and append registration record to CSV.
    Returns the saved record dict (without plaintext password).
    Raises ValueError on validation errors or Exception on IO errors.
    """

    patient_id ,patient_token = _generate_patient_id_and_token()
    parsed_visit_date = parse_iso_z(data["visit_date"])
    IST_visit_date = str(parsed_visit_date.date())
    print(f"PATIENT DB LOG :: IST visit date is {IST_visit_date}..........")
    year_week_dict = get_iso_week(parsed_visit_date)
    serial_number = get_patient_serial_number(doctor_id=data["doctor_id"].strip(),visit_date=IST_visit_date)
    
    record = {
        "patient_id":patient_id,
        "clinic_id": data["clinic_id"].strip(),
        "doctor_id": data["doctor_id"].strip(),
        "patient_name": data["patient_name"].strip(),
        "age": str(data["age"]),
        "sex": data["sex"].strip(),
        "occupation":"",
        "patient_address":"",
        "patient_mobile":data["patient_mobile"].strip(),
        "created_at": data["created_at"].strip(),
        "visit_day":data["visit_day"],
        "visit_date":IST_visit_date,
        "doctor_consultation_fees":data["clinic_fees"],
        "uTAN":patient_token,
        "serial_number":serial_number,
        "appointment_week":str(year_week_dict["week"]),
        "appointment_year":str(year_week_dict["year"]),
        "checked_in":data["checked_in"]
    }

    result = patient_db.insert_record(user_document=record)  # returns InsertOneResult or ObjectId
    inserted_id = getattr(result, "inserted_id", result)
    record_copy = dict(record)
    record_copy["_id"] = inserted_id

    return record_copy

def update_patient_profile(data: Dict) -> Dict:

    patient_id_raw = data.get("patient_id")
    if not patient_id_raw:
        patient_id ,patient_token = _generate_patient_id_and_token()
        print(f"PATIENT DB LOG :: IST visit date is {DATE_TODAY}..........")
        data['patient_id']=patient_id
        data['uTAN']=patient_token
        data['visit_date']=str(DATE_TODAY)
        data['appointment_week']=str(CURRENT_WEEK)
        data['appointment_year']=str(CURRENT_YEAR)
        data['created_at']=str(datetime.now(IST))

    print("PATIENT DB MANAGEMENT LOG : patient data...........")
    print(json.dumps(data))

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

def get_patient_by_doctor_id_clinic_id(doctor_id:str,clinic_id:str) -> Dict:
    patient_data_list = patient_db.find_by_two_fields(field1="doctor_id",val1=doctor_id,field2="clinic_id",val2=clinic_id)
    return patient_data_list


def get_patient_by_token_number(token_number:int) -> Dict:
    patient_data = patient_db.find_by_id(id_val=token_number,id_field="uTAN")
    return patient_data

def get_patient_serial_number(doctor_id:str,visit_date:str) -> int:
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

def get_patient_count_for_week(doctor_id:str,week:str) -> int:
    patient_list = patient_db.find_by_two_fields(field1="doctor_id",val1=doctor_id,field2="appointment_week",val2=week)
    if patient_list is None:
        raise ValueError(f"PATIENT DB LOG :: Could not process patient count for week = {week}, doctor_id = {doctor_id} invalid value passed to find_by_two_fields function!!")

    patient_count = len(patient_list)
    print(f"PATIENT DB LOG :: Returning total patient count:{patient_count} for week {week}")
    return patient_count

def get_patient_count_for_visit_date(doctor_id:str,date:str) -> int:
    patient_list = patient_db.find_by_two_fields(field1="doctor_id",val1=doctor_id,field2="visit_date",val2=date)
    if patient_list is None:
        raise ValueError(f"PATIENT DB LOG :: Could not process patient count for date = {date}, doctor_id = {doctor_id} invalid value passed to find_by_two_fields function!!")

    patient_count = len(patient_list)
    print(f"PATIENT DB LOG :: Returning total patient count:{patient_count} for date {date}")
    return patient_count