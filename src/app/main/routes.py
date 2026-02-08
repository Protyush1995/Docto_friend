import csv
import os, json
import random
from datetime import datetime
from io import BytesIO

from flask import (
    render_template,
    request,
    current_app,
    jsonify,
    session,
    redirect, 
    url_for,
)
from . import bp
from ..db_manager import doctor_database_management,clinic_database_management
from ..db_manager import db_operations




@bp.route("/", methods=["GET"])
def doctor_login_page():
    return render_template("doctor_login.html")

@bp.route("/doctor-login", methods=["POST"])
def api_doctor_login():
    
    data = request.get_json() or {}
    if len(data) == 0 : return jsonify(success=False, error="Empty request!! Contact ADMINISTRATOR!!"), 400
    
    #extracting login data
    identifier = (data.get("identifier") or "").strip()
    password = data.get("password") or ""
    remember = bool(data.get("remember"))

    # sanity check
    if not identifier or not password:
        return jsonify(success=False, error="missing_credentials"), 400

    try:
        res = doctor_database_management.authenticate_identifier(identifier, password)
        if not res.get("success"):
            # distinguish not found vs invalid credentials
            err = res.get("error", "invalid_credentials")
            return jsonify(success=False, error=err), 401

        user = res["user"]
        
        # Assigning session doctor_id
        session.clear()
        session["doctor_id"] = user["doctor_id"]
        
        # set a flag for "remember" if requested (requires configuring permanent_session_lifetime)
        if remember:
            session.permanent = True

        current_app.logger.info("Doctor %s logged in", session.get("doctor_id"))
        return jsonify(success=True, user_id=user["doctor_id"], redirect=url_for('main.doc_dashboard', doctor_id=user["doctor_id"])), 200

    except Exception:
        current_app.logger.exception("Login error")
        return jsonify(success=False, error="internal_error"), 500

@bp.route("/doctor-register", methods=["GET"])
def doctor_registration_form():
    return render_template("doctor_registration.html")

@bp.route("/doctor-register", methods=["POST"])
def register_route():
    data = request.get_json() or {}
    try:
        rec = doctor_database_management.append_registration_record(data)
        # TODO: send verification email asynchronously
        return jsonify(success=True, doctor_id=rec["doctor_id"]), 201
    except ValueError as ve:
        return jsonify(success=False, error=str(ve)), 400
    except Exception as e:
        current_app.logger.exception("Failed to save registration")
        return jsonify(success=False, error="internal_error"), 500

@bp.route("/doctor-edit-profile/<doctor_id>/edit", methods=["GET"])
def doctor_edit_profile_form(doctor_id):
    # load from DB using your existing DB helper
    data = doctor_database_management.get_doctor_by_id(doctor_id)
    if not data:
        abort(404)

    if "image_data" in data:
        profile_pic_uri = clinic_database_management.base64_string_to_data_uri(data["image_data"],data['image_mime'])
    else:
        profile_pic_uri = "Profile Picture Placeholder"

    return render_template("doctor_edit_profile.html", doctor_data=data, profile_pic_uri=profile_pic_uri)

@bp.route("/doctor-edit-profile/", methods=["POST"])
def doctor_update_profile():
    data = request.get_json() or {}
    print(f"ROUTE LOG : Printing from doctor_update_profile from routes-------------------------------{json.dumps(data)}")
    try:
        response = doctor_database_management.update_doctor_profile(data)
        print(f"ROUTE LOG : Printing response from update profile from routes-------------------------------{json.dumps(response)}")
        # TODO: send verification email asynchronously
        if response["success"] :
            return jsonify(success=True,user_id=response.get("doctor_id"),message="Profile update successfull"), 201
        else: return jsonify(success=False,user_id=response.get("doctor_id"),message="Problem updating profile"), 201
    except ValueError as ve:
        return jsonify(success=False, error=str(ve)), 400
    except Exception as e:
        current_app.logger.exception("Failed to update doctor profile !! Contact Admin!!")
        return jsonify(success=False, error="internal_error"), 500

@bp.route("/doctor-forgot-password", methods=["GET"])
def doctor_forgot_password_page():
    return render_template("doctor_forgot_password.html")

@bp.route("/doctor-clinic-seeding", methods=["GET", "POST"])
def doctor_clinic_seed_form():
    if 'doctor_id' not in session:
        return redirect(url_for('main.doctor_login_page'))

    if request.method == "POST":
        doctor_id = session.get("doctor_id")
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error":"invalid json"}), 400

        clinic_name = data.get("clinicName")
        clinic_contact = data.get("clinicContact")
        clinic_contact_alternative = data.get("clinicContactAlt")
        clinic_fees = data.get("clinicFees")
        clinic_email = data.get("clinicemail")

        address = {
            "house_no": data.get("houseNo"),
            "street": data.get("street"),
            "post_office": data.get("postOffice"),
            "police_station": data.get("policeStation"),
            "city": data.get("city"),
            "pin_code": data.get("pinCode"),
            "state": data.get("state"),
            "country": data.get("country")
        }

        # schedule comes as object under "schedule"
        schedule = data.get("schedule")

        clinic_data = {
            "clinic_name": clinic_name,
            "clinic_contact": clinic_contact,
            "clinic_contact_alternative":clinic_contact_alternative,
            "clinic_email":clinic_email,
            "clinic_fees": clinic_fees,
            "clinic_address": address,
            "visit_schedule": schedule,
            "doctor_id":doctor_id,
        }

        # Save to DB
        response = clinic_database_management.append_clinic_registration_record(clinic_data)
        print("Inserted clinic:", response)
        return jsonify(success=True,doctor_id=doctor_id,message="Clinic has been inserted successfully!!",redirect=True), 201

    username=session.get("doctor_id")
    #print("Printing username from add clinic................!!!!!!!!!!!")
    #print(username)
    doctor_data=doctor_database_management.get_doctor_by_id(doctor_id=username)
    return render_template(
        "doctor_add_clinic.html",
        username=username,
        doctor_data=doctor_data
    )

@bp.route("/clinic-booking", methods=["GET"])
def clinic_booking():

    clinic_id = request.args.get("clinic_id", "").strip()
    doctor_id = request.args.get("doctor_id", "").strip()

    if not clinic_id or not doctor_id : return jsonify({"error": "Arguments missing! Clinic ID or Doctor ID missing!!"}), 404
    
    doctor_data = doctor_database_management.get_doctor_by_id(doctor_id=doctor_id)
    clinic_data = clinic_database_management.get_clinic_by_clinic_id(clinic_id=clinic_id)

    if not doctor_data or not clinic_data : return jsonify({"WARNING": "Clinic Data or Doctor Data missing!!"}), 404
    
    if "image_data" in doctor_data:
        profile_pic_uri = clinic_database_management.base64_string_to_data_uri(doctor_data["image_data"],doctor_data['image_mime'])
    else:
        profile_pic_uri = None

    clinic_address = dict_to_string(d=clinic_data["clinic_address"],fmt="vo")
    visit_schedule = dict_to_string(d=clinic_data["visit_schedule"],fmt="vo")

    return render_template("clinic_booking.html",doctor_data=doctor_data,clinic_data=clinic_data,profile_pic_uri=profile_pic_uri,clinic_address=clinic_address,visit_schedule=visit_schedule) 

@bp.route("/send-otp", methods=["POST"])
def send_otp():
    mobile = request.form.get("mobile", "").strip()
    if not mobile or not mobile.isdigit() or len(mobile) < 10:
        return jsonify({"error": "invalid_mobile"}), 400
    otp = str(random.randint(100000, 999999))
    session["booking_otp"] = otp
    session["booking_mobile"] = mobile
    current_app.logger.info("Generated OTP for %s", mobile)
    # For testing we return otp; replace with SMS provider in production
    return jsonify({"otp": otp}), 200

@bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    otp = request.form.get("otp", "").strip()
    if not otp:
        return jsonify({"verified": False, "error": "missing_otp"}), 400
    if session.get("booking_otp") == otp:
        session.pop("booking_otp", None)
        session["otp_verified"] = True
        return jsonify({"verified": True}), 200
    return jsonify({"verified": False}), 400

@bp.route("/submit-booking", methods=["POST"])
def submit_booking():
    if not session.get("otp_verified"):
        return jsonify({"error": "otp_not_verified"}), 400

    qr = request.form.get("qr", "").strip()
    patient_name = request.form.get("patient_name", "").strip()
    patient_mobile = session.get("booking_mobile", "").strip()
    visit_day = request.form.get("doctor_visit_day", "").strip()

    if not qr or not patient_name or not patient_mobile:
        return jsonify({"error": "missing_fields"}), 400

    csv_path = os.path.join(os.path.dirname(__file__), "..", "db_manager", "doctor_db_dataframe.csv")
    if not os.path.exists(csv_path):
        return jsonify({"error": "record_not_found"}), 404

    record = None
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("qr_filename") == qr:
                record = r
                break

    if not record:
        return jsonify({"error": "record_not_found"}), 404

    ts = datetime.utcnow().strftime("%Y%m%d")

    def _safe(s: str) -> str:
        return "".join(c for c in (s or "") if c.isalnum() or c in " _-").strip().replace(" ", "_")

    clinic_id = record.get("clinic_id", "clinic")
    clinic_name = _safe(record.get("clinic_name", ""))
    doctor_name = _safe(record.get("doctor_name", ""))
    booking_filename = f"{clinic_id}__{clinic_name}__{doctor_name}__{ts}.csv"

    booking_dir = os.path.join(os.path.dirname(__file__), "..", "db_manager")
    os.makedirs(booking_dir, exist_ok=True)
    booking_path = os.path.join(booking_dir, booking_filename)

    patient_id = f"P{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}"

    headers = [
        "patient_id",
        "patient_name",
        "patient_mobile",
        "visit_day",
        "clinic_id",
        "clinic_name",
        "clinic_address",
        "doctor_name",
        "doctor_qualifications",
        "created_at",
    ]
    row = {
        "patient_id": patient_id,
        "patient_name": patient_name,
        "patient_mobile": patient_mobile,
        "visit_day": visit_day,
        "clinic_id": record.get("clinic_id", ""),
        "clinic_name": record.get("clinic_name", ""),
        "clinic_address": record.get("clinic_address", ""),
        "doctor_name": record.get("doctor_name", ""),
        "doctor_qualifications": record.get("doctor_qualifications", ""),
        "created_at": datetime.utcnow().isoformat(),
    }

    write_header = not os.path.exists(booking_path)
    with open(booking_path, "a", newline="", encoding="utf-8") as bf:
        writer = csv.DictWriter(bf, fieldnames=headers)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    session.pop("otp_verified", None)
    session.pop("booking_mobile", None)

    current_app.logger.info("Saved booking %s to %s", patient_id, booking_filename)
    return jsonify({"patient_id": patient_id, "booking_file": booking_filename}), 200

@bp.route('/doc_dashboard/<doctor_id>', methods=["GET"])
def doc_dashboard(doctor_id):
    if not doctor_id:
        return redirect(url_for('main.doctor_login_page'))
    
    doctor_data = doctor_database_management.get_doctor_by_id(doctor_id)
    clinics_list = clinic_database_management.get_clinic_by_doctor_id(doctor_id)
    print(f"ROUTE LOG : Printing clinic list TYPE from doctor dashboard route::list type = {type(clinics_list)}")

    if isinstance(clinics_list, dict):
        clinics_list = [clinics_list]

    #Converting schedules for ease of display
    for clinic in clinics_list:
        clinic["clinic_address"] = dict_to_string(d=clinic["clinic_address"],fmt="vo")
        clinic["visit_schedule"] = dict_to_string(d=clinic["visit_schedule"],fmt="kv")

    
    filtered_list = [remove_bytes_from_dict(x) for x in clinics_list ]
    print(f"ROUTE LOG : Printing clinic list from doctor dashboard::list type = {type(filtered_list)} ::: {filtered_list}")
    doctor_data['clinics'] = filtered_list

    if "image_data" in doctor_data:
        profile_pic_uri = clinic_database_management.base64_string_to_data_uri(doctor_data["image_data"],doctor_data['image_mime'])
    else:
        profile_pic_uri = None

    print(f"ROUTE LOG : Generated profile pic uri = {profile_pic_uri}")
    
    
    return render_template(
        'doctor_dashboard.html',
        user_id=doctor_id,
        profile_pic_uri=profile_pic_uri,
        doctor_data=doctor_data,
        clinics = filtered_list
    )

@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()  # Clear the session
    return redirect(url_for('main.doctor_login_page'))  # Redirect to login page

@bp.route('/doc_clinic_update/<doctor_id>/<clinic_id>', methods=["GET"])
def doc_clinic_update(doctor_id:str,clinic_id:str):
    if not doctor_id or not clinic_id:
        return redirect(url_for('main.doctor_login_page'))
    
    doctor_data = doctor_database_management.get_doctor_by_id(doctor_id)
    clinic = clinic_database_management.get_clinic_by_clinic_id(clinic_id)
    print(f"ROUTE LOG : Printing clinic list TYPE from doctor dashboard route::list type = {type(clinic)}")
    """
    if isinstance(clinics_list, dict):
        clinics_list = [clinics_list]

    #Converting schedules for ease of display
    for clinic in clinics_list:
        clinic["clinic_address"] = dict_to_string(d=clinic["clinic_address"],fmt="vo")
        clinic["visit_schedule"] = dict_to_string(d=clinic["visit_schedule"],fmt="kv")

    
    filtered_list = [remove_bytes_from_dict(x) for x in clinics_list ]
    print(f"ROUTE LOG : Printing clinic list from doctor dashboard::list type = {type(filtered_list)} ::: {filtered_list}")
    doctor_data['clinics'] = filtered_list

    if "image_data" in doctor_data:
        profile_pic_uri = clinic_database_management.base64_string_to_data_uri(doctor_data["image_data"],doctor_data['image_mime'])
    else:
        profile_pic_uri = None

    print(f"ROUTE LOG : Generated profile pic uri = {profile_pic_uri}")"""
    
    
    return render_template(
        'doctor_clinic_update.html',
        user_id=doctor_id,
        doctor_data=doctor_data,
        clinic = clinic
    )

#helper functions
def dict_to_string(d: dict, fmt: str = "vo") -> str:
    """
    Convert dict to string.
    fmt="kv" -> "KEY1 , Val1 . KEY2 , Val2" (key value pair, in insertion order)
    fmt="vo" -> "Val1,Val2,Val3"  (values only, in insertion order)
    """
    if not isinstance(d, dict):
        raise TypeError("d must be a dict")
    if fmt == "kv":
        parts = [f"{k} : {v}" for k, v in d.items()]
        return " . ".join(parts)
    elif fmt == "vo":
        vals = [str(v) for v in d.values()]
        return ", ".join(vals)
    else:
        raise ValueError("fmt must be 'kv' or 'vo'")

def remove_bytes_from_dict(d: dict) -> dict:
    return {k: v for k, v in d.items() if not isinstance(v, bytes)}