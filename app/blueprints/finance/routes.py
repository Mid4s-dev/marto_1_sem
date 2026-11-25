"""
Finance blueprint — payment posting, M-Pesa validation, dynamic balance,
charges management, and tenant statement view.
"""
import hmac
import re
import secrets
from datetime import datetime

from flask import (
    Blueprint, render_template, redirect, url_for, current_app, jsonify,
    request, flash, abort,
)
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
import requests

from app.models import db, Lease, Payment, Charge, User
from app.blueprints.auth.routes import role_required

finance_bp = Blueprint("finance", __name__, template_folder="../../templates")

MPESA_REGEX = re.compile(r"^[A-Z0-9]{10}$")


@finance_bp.route("/payments/verify", methods=["GET", "POST"])
@login_required
def verify_payment():
    payment = None
    code = ""
    if request.method == "POST":
        code = request.form.get("mpesa_code", "").strip().upper()
        payment = Payment.query.filter_by(mpesa_code=code).first()
    return render_template(
        "public_verify_payment.html",
        payment=payment,
        code=code,
    )


def _normalize_phone(phone):
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("0") and len(digits) == 10:
        return "254" + digits[1:]
    if digits.startswith("254") and len(digits) == 12:
        return digits
    return None


# ---------------------------------------------------------------------------
# IntaSend M-Pesa checkout
# ---------------------------------------------------------------------------
@finance_bp.route("/payments/intasend", methods=["POST"])
@login_required
@role_required("Tenant")
def intasend_checkout():
    lease = Lease.query.filter_by(
        tenant_user_id=current_user.user_id,
        active_status=True,
    ).first()
    if not lease:
        flash("You do not have an active lease.", "danger")
        return redirect(url_for("finance.tenant_statement"))

    secret_key = current_app.config.get("INTASEND_SECRET_KEY", "")
    if not secret_key:
        flash("IntaSend is not configured. Add INTASEND_SECRET_KEY first.", "danger")
        return redirect(url_for("finance.tenant_statement"))

    phone_number = _normalize_phone(request.form.get("phone_number", ""))
    if not phone_number:
        flash("Enter a valid Kenyan phone number.", "danger")
        return redirect(url_for("finance.tenant_statement"))

    try:
        amount = float(request.form.get("amount", "0"))
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Amount must be a positive number.", "danger")
        return redirect(url_for("finance.tenant_statement"))

    api_ref = f"LS{lease.lease_id}{secrets.token_hex(3)}".upper()[:10]
    endpoint = current_app.config["INTASEND_BASE_URL"].rstrip("/") + "/payment/mpesa-stk-push/"
    try:
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {secret_key}",
                "Content-Type": "application/json",
            },
            json={
                "amount": round(amount),
                "phone_number": phone_number,
                "api_ref": api_ref,
            },
            timeout=20,
        )
    except requests.RequestException:
        current_app.logger.exception("IntaSend STK push request failed")
        flash("Could not connect to IntaSend. Please try again.", "danger")
        return redirect(url_for("finance.tenant_statement"))

    if not response.ok:
        current_app.logger.warning("IntaSend rejected checkout: %s", response.text[:500])
        flash("IntaSend could not start the M-Pesa prompt.", "danger")
        return redirect(url_for("finance.tenant_statement"))

    invoice = response.json().get("invoice", {})
    if not invoice.get("invoice_id"):
        flash("IntaSend returned an incomplete payment response.", "danger")
        return redirect(url_for("finance.tenant_statement"))

    flash(
        f"M-Pesa prompt sent to {phone_number}. Invoice {api_ref} is pending.",
        "success",
    )
    return redirect(url_for("finance.tenant_statement"))


@finance_bp.route("/payments/intasend/webhook", methods=["POST"])
def intasend_webhook():
    event = request.get_json(silent=True)
    if not isinstance(event, dict):
        return jsonify({"error": "invalid JSON"}), 400

    challenge = current_app.config.get("INTASEND_WEBHOOK_CHALLENGE", "")
    supplied_challenge = str(event.get("challenge", ""))
    if challenge and not hmac.compare_digest(supplied_challenge, challenge):
        return jsonify({"error": "invalid challenge"}), 401

    if event.get("topic") != "collection_event" or event.get("state") != "COMPLETE":
        return jsonify({"received": True}), 200

    api_ref = str(event.get("api_ref", "")).upper()
    if not api_ref:
        return jsonify({"error": "missing api_ref"}), 400

    payment_code = api_ref[:10]
    if Payment.query.filter_by(mpesa_code=payment_code).first():
        return jsonify({"received": True, "duplicate": True}), 200

    lease_id_match = re.match(r"^LS(\d+)", api_ref)
    if not lease_id_match:
        return jsonify({"error": "invalid api_ref"}), 400

    lease = db.session.get(Lease, int(lease_id_match.group(1)))
    if not lease or not lease.active_status:
        return jsonify({"error": "lease not found"}), 404

    amount = float(event.get("value", 0) or 0)
    if amount <= 0:
        return jsonify({"error": "invalid amount"}), 400

    payment = Payment(
        lease_id=lease.lease_id,
        amount=amount,
        mpesa_code=payment_code,
        payment_date=datetime.utcnow(),
        verified_by_user_id=None,
    )
    db.session.add(payment)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"received": True, "duplicate": True}), 200

    return jsonify({"received": True}), 200


# ---------------------------------------------------------------------------
# Post a payment (Caretaker)
# ---------------------------------------------------------------------------
@finance_bp.route("/payments/post", methods=["GET", "POST"])
@login_required
@role_required("Caretaker", "Landlord")
def post_payment():
    active_leases = Lease.query.filter_by(active_status=True).all()

    if request.method == "POST":
        lease_id = request.form.get("lease_id", type=int)
        amount = request.form.get("amount", "0")
        mpesa_code = request.form.get("mpesa_code", "").strip().upper()

        # --- Validation ---
        if not MPESA_REGEX.match(mpesa_code):
            flash("Invalid M-Pesa code. Must be exactly 10 uppercase alphanumeric characters.", "danger")
            return render_template("caretaker/post_payment.html", leases=active_leases)

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Amount must be a positive number.", "danger")
            return render_template("caretaker/post_payment.html", leases=active_leases)

        lease = Lease.query.get_or_404(lease_id)

        payment = Payment(
            lease_id=lease.lease_id,
            amount=amount,
            mpesa_code=mpesa_code,
            payment_date=datetime.utcnow(),
            verified_by_user_id=current_user.user_id,
        )
        db.session.add(payment)

        try:
            db.session.commit()
            flash(f"Payment {mpesa_code} (KES {amount:,.2f}) posted successfully.", "success")
            return redirect(url_for("finance.post_payment"))
        except IntegrityError:
            db.session.rollback()
            flash(f"M-Pesa code {mpesa_code} has already been recorded. Duplicate rejected.", "danger")
            return render_template("caretaker/post_payment.html", leases=active_leases)

    return render_template("caretaker/post_payment.html", leases=active_leases)


# ---------------------------------------------------------------------------
# Tenant: personal statement / ledger
# ---------------------------------------------------------------------------
@finance_bp.route("/statement")
@login_required
@role_required("Tenant")
def tenant_statement():
    lease = (
        Lease.query
        .filter_by(tenant_user_id=current_user.user_id, active_status=True)
        .first()
    )
    if not lease:
        flash("You have no active lease.", "info")
        return render_template("tenant/statement.html", lease=None)

    charges = lease.charges.order_by(Charge.due_date.asc()).all()
    payments = lease.payments.order_by(Payment.payment_date.asc()).all()
    balance = lease.balance

    return render_template(
        "tenant/statement.html",
        lease=lease,
        charges=charges,
        payments=payments,
        balance=balance,
    )


# ---------------------------------------------------------------------------
# Landlord: all payments listing
# ---------------------------------------------------------------------------
@finance_bp.route("/payments")
@login_required
@role_required("Landlord")
def all_payments():
    payments = Payment.query.order_by(Payment.payment_date.desc()).all()
    return render_template("landlord/payments.html", payments=payments)


# ---------------------------------------------------------------------------
# Add charge to a lease (Landlord / Caretaker)
# ---------------------------------------------------------------------------
@finance_bp.route("/charges/add", methods=["GET", "POST"])
@login_required
@role_required("Landlord", "Caretaker")
def add_charge():
    active_leases = Lease.query.filter_by(active_status=True).all()

    if request.method == "POST":
        lease_id = request.form.get("lease_id", type=int)
        charge_type = request.form.get("charge_type", "").strip()
        amount = request.form.get("amount", "0")
        due_date_str = request.form.get("due_date", "")

        try:
            amount = float(amount)
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid amount or date.", "danger")
            return render_template("caretaker/add_charge.html", leases=active_leases)

        charge = Charge(
            lease_id=lease_id,
            charge_type=charge_type,
            amount=amount,
            due_date=due_date,
        )
        db.session.add(charge)
        db.session.commit()
        flash(f"Charge '{charge_type}' of KES {amount:,.2f} added.", "success")
        return redirect(url_for("finance.add_charge"))

    return render_template("caretaker/add_charge.html", leases=active_leases)


# ---------------------------------------------------------------------------
# Arrears report (Landlord)
# ---------------------------------------------------------------------------
@finance_bp.route("/arrears")
@login_required
@role_required("Landlord")
def arrears_report():
    active_leases = Lease.query.filter_by(active_status=True).all()
    arrears = [l for l in active_leases if l.balance > 0]
    return render_template("landlord/arrears.html", arrears=arrears)
