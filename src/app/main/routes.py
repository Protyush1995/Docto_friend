'''

#new imports
import csv
import os
import random
from datetime import datetime
from flask import flash, redirect, url_for, jsonify, session

#old imports
from flask import render_template, request, current_app
from . import bp
from ..db_manager import doctor_db_manager

#old working routes 
@bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@bp.route("/doctor-seed", methods=["GET"])
def doctor_seed_form():
    return render_template("doctor_db_seed.html")

@bp.route("/doctor-seed", methods=["POST"])
def doctor_seed_submit():
    fields = {
        "doctor_id": request.form.get("doctor_id", "").strip(),
        "doctor_name": request.form.get("doctor_name", "").strip(),
        "doctor_qualifications": request.form.get("doctor_qualifications", "").strip(),
        "clinic_id": request.form.get("clinic_id", "").strip(),
        "clinic_name": request.form.get("clinic_name", "").strip(),
        "clinic_fees": request.form.get("clinic_fees", "").strip(),
        "clinic_address": request.form.get("clinic_address", "").strip(),
        "clinic_contact": request.form.get("clinic_contact", "").strip(),
        "doctor_visit_days": request.form.get("doctor_visit_days", "").strip(),
    }

    try:
        qr_filename = doctor_db_manager.append_doctor_record(fields)
        current_app.logger.info("Saved QR: %s", qr_filename)
        message = f"Saved. CSV updated; QR image: {qr_filename}"
        return render_template("doctor_db_seed.html", success_message=message, qr_filename=qr_filename)
    except Exception as e:
        current_app.logger.exception("Failed to save doctor record")
        return render_template("doctor_db_seed.html", error_message=str(e)), 500
#old working routes end

# new route: view clinic booking by QR filename (qr param)
@bp.route("/clinic-booking")
def clinic_booking():
    qr = request.args.get("qr", "")
    if not qr:
        return render_template("clinic_booking.html", error_message="Missing qr"), 400

    # locate CSV and find record by qr_filename
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

    # prepare visit days list
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
    # In production send SMS; here we return otp for testing
    return jsonify({"otp": otp}), 200

@bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    otp = request.form.get("otp", "").strip()
    if session.get("booking_otp") == otp:
        session.pop("booking_otp", None)
        session["otp_verified"] = True
        return jsonify({"verified": True}), 200
    return jsonify({"verified": False}), 400

@bp.route("/submit-booking", methods=["POST"])
def submit_booking():
    if not session.get("otp_verified"):
        return jsonify({"error": "otp_not_verified"}), 400

    qr = request.form.get("qr", "")
    patient_name = request.form.get("patient_name", "").strip()
    patient_mobile = session.get("booking_mobile", "")
    visit_day = request.form.get("doctor_visit_day", "").strip()
    if not patient_name or not patient_mobile:
        return jsonify({"error": "missing_fields"}), 400

    # find doctor/clinic record (same lookup as clinic_booking)
    csv_path = os.path.join(os.path.dirname(__file__), "..", "db_manager", "doctor_db_dataframe.csv")
    record = None
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("qr_filename") == qr:
                record = r
                break
    if not record:
        return jsonify({"error": "record_not_found"}), 404

    # prepare booking CSV filename
    ts = datetime.utcnow().strftime("%Y%m%d")
    safe = lambda s: "".join(c for c in s if c.isalnum() or c in " _-").strip().replace(" ", "_")
    clinic_id = record.get("clinic_id", "clinic")
    clinic_name = safe(record.get("clinic_name", ""))
    doctor_name = safe(record.get("doctor_name", ""))
    booking_filename = f"{clinic_id}__{clinic_name}__{doctor_name}__{ts}.csv"
    booking_dir = os.path.join(os.path.dirname(__file__), "..", "db_manager")
    os.makedirs(booking_dir, exist_ok=True)
    booking_path = os.path.join(booking_dir, booking_filename)

    # generate patient_id
    patient_id = f"P{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}"

    # write header if file not exists
    headers = [
        "patient_id","patient_name","patient_mobile","visit_day",
        "clinic_id","clinic_name","clinic_address",
        "doctor_name","doctor_qualifications","created_at"
    ]
    row = {
        "patient_id": patient_id,
        "patient_name": patient_name,
        "patient_mobile": patient_mobile,
        "visit_day": visit_day,
        "clinic_id": record.get("clinic_id",""),
        "clinic_name": record.get("clinic_name",""),
        "clinic_address": record.get("clinic_address",""),
        "doctor_name": record.get("doctor_name",""),
        "doctor_qualifications": record.get("doctor_qualifications",""),
        "created_at": datetime.utcnow().isoformat(),
    }
    write_header = not os.path.exists(booking_path)
    with open(booking_path, "a", newline="", encoding="utf-8") as bf:
        writer = csv.DictWriter(bf, fieldnames=headers)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    # clear otp_verified
    session.pop("otp_verified", None)
    return jsonify({"patient_id": patient_id, "booking_file": booking_filename}), 200
 
Docstring for src.app.main.routes
'''

#new gpt provided file

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
    url_for,
)
from . import bp
from ..db_manager import doctor_db_manager


@bp.route("/", methods=["GET"])
def index():
    return render_template("docto_login.html")


@bp.route("/doctor-seed", methods=["GET"])
def doctor_seed_form():
    return render_template("doctor_db_seed.html")


@bp.route("/doctor-seed", methods=["POST"])
def doctor_seed_submit():
    fields = {
        "doctor_id": request.form.get("doctor_id", "").strip(),
        "doctor_first_name": request.form.get("doctor_first_name", "").strip(),
        "doctor_last_name": request.form.get("doctor_last_name", "").strip(),
        "doctor_qualifications": request.form.get("doctor_qualifications", "").strip(),
        "clinic_id": request.form.get("clinic_id", "").strip(),
        "clinic_name": request.form.get("clinic_name", "").strip(),
        "clinic_fees": request.form.get("clinic_fees", "").strip(),
        "clinic_address": request.form.get("clinic_address", "").strip(),
        "clinic_contact": request.form.get("clinic_contact", "").strip(),
        "doctor_visit_days": request.form.get("doctor_visit_days", "").strip(),
    }

    try:
        qr_filename = doctor_db_manager.append_doctor_record(fields)
        # Store form data in session
        session['last_submitted_data'] = fields
        
        current_app.logger.info("Saved QR: %s", qr_filename)
        message = f"Saved. CSV updated; QR image: {qr_filename}"
        dashboard_url = url_for('main.doc_seed_dashboard')  # Update with the correct blueprint name
        return render_template("doctor_db_seed.html", success_message=message, qr_filename=qr_filename, dashboard_url=dashboard_url)
        
    except Exception as e:
        current_app.logger.exception("Failed to save doctor record")
        return render_template("doctor_db_seed.html", error_message=str(e)), 500


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

@bp.route("/doc-seed-dashboard")
def doc_seed_dashboard():
    doctor_data = session.get('last_submitted_data', {})
    return render_template("doctor_dashboard.html", doctor_data=doctor_data)