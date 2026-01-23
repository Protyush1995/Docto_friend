import csv
import os
import random
from datetime import datetime

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
from ..db_manager import doctor_database_management


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
        print("Printing user data returned")
        print(user)
        # minimal session assignment
        session.clear()
        for k, v in user.items(): session[k] = v
        #session["doctor_name"] = f"{session.get('firstname','')} {session.get('lastname','')}".strip()
        
        # set a flag for "remember" if requested (requires configuring permanent_session_lifetime)
        if remember:
            session.permanent = True

        current_app.logger.info("Doctor %s logged in", session.get("doctor_id"))
        return jsonify(success=True, redirect=url_for('main.doc_dashboard')), 200

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

@bp.route("/doctor-edit-profile", methods=["GET"])
def doctor_edit_profile_form():
    return render_template("doctor_edit_profile.html")

@bp.route("/doctor-forgot-password", methods=["GET"])
def doctor_forgot_password_page():
    return render_template("doctor_forgot_password.html")

@bp.route("/doctor-clinic-seeding", methods=["GET"])
def doctor_clinic_seed_form():
    # Ensure user is logged in
    if 'doctor_id' not in session:
        print("from doctor_clinic_seed_form......................")
        print(session)
        return redirect(url_for('main.doctor_login_page'))

    return render_template(
        "doctor_add_clinic.html",
        username=session.get("doctor_id"),
        doctor_data=dict(session)
    )

@bp.route("/clinic-booking", methods=["GET"])
def clinic_booking():
    qr = request.args.get("qr", "").strip()
    if not qr:
        return render_template("clinic_booking.html", error_message="Missing qr parameter"), 400

    csv_path = os.path.join(os.path.dirname(__file__), "..", "db_manager", "doctor_db_dataframe.csv")
    record = None
    if os.path.exists(csv_path):
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("qr_filename") == qr:
                    record = r
                    break

    if not record:
        return render_template("clinic_booking.html", error_message="Record not found"), 404

    days = [d.strip() for d in (record.get("doctor_visit_days") or "").split(",") if d.strip()]
    return render_template("clinic_booking.html", record=record, visit_days=days)

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

@bp.route('/doc_dashboard')
def doc_dashboard():
    user_id = session.get('doctor_id')

    if not user_id:
        return redirect(url_for('main.doctor_login_page'))
    
    doctor_data = dict(session)
    print("Printing doctor data from routes.py doc_dashboard")
    print(doctor_data)
    #clinics_list = find_clinics_by_doctor(user_id)
    #doctor_data['clinics'] = clinics_list
   
    return render_template(
        'doctor_dashboard.html',
        user_id=user_id,
        doctor_data=doctor_data
        #clinics = clinics_list
    )

@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()  # Clear the session
    return redirect(url_for('main.doctor_login_page'))  # Redirect to login page