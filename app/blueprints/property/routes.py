"""
Property blueprint — unit CRUD, lease assignment.
Landlord and Caretaker roles only.
"""
from datetime import date

from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash,
)
from flask_login import login_required, current_user

from app.models import db, Unit, Lease, User, Charge
from app.blueprints.auth.routes import role_required

property_bp = Blueprint("property", __name__, template_folder="../../templates")


@property_bp.route("/available")
def public_vacancies():
    vacant_units = Unit.query.filter_by(status="Vacant").order_by(Unit.unit_number).all()
    return render_template(
        "public_vacancies.html",
        vacant_units=vacant_units,
    )


# ---------------------------------------------------------------------------
# Landlord dashboard
# ---------------------------------------------------------------------------
@property_bp.route("/landlord")
@login_required
@role_required("Landlord")
def landlord_dashboard():
    units = Unit.query.order_by(Unit.unit_number).all()
    tenants = User.query.join(User.role).filter_by(role_name="Tenant").all()

    # Arrears: leases where balance > 0
    active_leases = Lease.query.filter_by(active_status=True).all()
    arrears = [l for l in active_leases if l.balance > 0]

    return render_template(
        "landlord/dashboard.html",
        units=units,
        arrears=arrears,
        tenants=tenants,
    )


# ---------------------------------------------------------------------------
# Caretaker dashboard
# ---------------------------------------------------------------------------
@property_bp.route("/caretaker")
@login_required
@role_required("Caretaker")
def caretaker_dashboard():
    units = Unit.query.order_by(Unit.unit_number).all()
    tenants = User.query.join(User.role).filter_by(role_name="Tenant").all()
    return render_template("caretaker/dashboard.html", units=units, tenants=tenants)


# ---------------------------------------------------------------------------
# Units — CRUD (Landlord + Caretaker)
# ---------------------------------------------------------------------------
@property_bp.route("/units")
@login_required
@role_required("Landlord", "Caretaker")
def list_units():
    units = Unit.query.order_by(Unit.unit_number).all()
    return render_template("landlord/units.html", units=units)


@property_bp.route("/units/add", methods=["GET", "POST"])
@login_required
@role_required("Landlord")
def add_unit():
    if request.method == "POST":
        unit_number = request.form.get("unit_number", "").strip().upper()
        monthly_rent = request.form.get("monthly_rent", "0")
        deposit = request.form.get("deposit", "0")
        description = request.form.get("description", "").strip()
        image_url = request.form.get("image_url", "").strip()
        bedrooms = request.form.get("bedrooms", "1", type=int)
        bathrooms = request.form.get("bathrooms", "1", type=int)
        status = request.form.get("status", "Vacant")

        if not unit_number:
            flash("Unit number is required.", "danger")
            return render_template("landlord/unit_form.html", unit=None)

        if Unit.query.filter_by(unit_number=unit_number).first():
            flash(f"Unit {unit_number} already exists.", "danger")
            return render_template("landlord/unit_form.html", unit=None)

        unit = Unit(
            unit_number=unit_number,
            monthly_rent=float(monthly_rent),
            deposit=float(deposit),
            description=description,
            image_url=image_url or None,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            status=status,
        )
        db.session.add(unit)
        db.session.commit()
        flash(f"Unit {unit_number} created.", "success")
        return redirect(url_for("property.list_units"))

    return render_template("landlord/unit_form.html", unit=None)


@property_bp.route("/units/<int:unit_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("Landlord", "Caretaker")
def edit_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)

    if request.method == "POST":
        unit.monthly_rent = float(request.form.get("monthly_rent", unit.monthly_rent))
        unit.deposit = float(request.form.get("deposit", unit.deposit))
        unit.description = request.form.get("description", unit.description).strip()
        unit.image_url = request.form.get("image_url", unit.image_url or "").strip() or None
        unit.bedrooms = request.form.get("bedrooms", unit.bedrooms, type=int)
        unit.bathrooms = request.form.get("bathrooms", unit.bathrooms, type=int)
        unit.status = request.form.get("status", unit.status)
        db.session.commit()
        flash(f"Unit {unit.unit_number} updated.", "success")
        return redirect(url_for("property.list_units"))

    return render_template("landlord/unit_form.html", unit=unit)


# ---------------------------------------------------------------------------
# Leases
# ---------------------------------------------------------------------------
@property_bp.route("/leases")
@login_required
@role_required("Landlord", "Caretaker")
def list_leases():
    leases = Lease.query.filter_by(active_status=True).all()
    return render_template("landlord/leases.html", leases=leases)


@property_bp.route("/leases/assign", methods=["GET", "POST"])
@login_required
@role_required("Landlord", "Caretaker")
def assign_lease():
    vacant_units = Unit.query.filter_by(status="Vacant").all()
    tenants = (
        User.query.join(User.role)
        .filter_by(role_name="Tenant")
        .all()
    )

    if request.method == "POST":
        tenant_id = request.form.get("tenant_id", type=int)
        unit_id = request.form.get("unit_id", type=int)
        start_date_str = request.form.get("start_date", "")

        unit = Unit.query.get_or_404(unit_id)
        tenant = User.query.get_or_404(tenant_id)

        if unit.status == "Occupied":
            flash("Unit is already occupied.", "danger")
            return render_template("caretaker/assign_lease.html", units=vacant_units, tenants=tenants)

        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            flash("Invalid start date.", "danger")
            return render_template("caretaker/assign_lease.html", units=vacant_units, tenants=tenants)

        lease = Lease(tenant_user_id=tenant.user_id, unit_id=unit.unit_id, start_date=start_date)
        unit.status = "Occupied"
        db.session.add(lease)

        # Auto-generate first month rent charge
        charge = Charge(
            lease=lease,
            charge_type="Monthly Rent",
            amount=unit.monthly_rent,
            due_date=start_date,
        )
        db.session.add(charge)
        db.session.commit()
        flash(f"Lease assigned: {tenant.email} → Unit {unit.unit_number}.", "success")
        return redirect(url_for("property.list_leases"))

    return render_template("caretaker/assign_lease.html", units=vacant_units, tenants=tenants)


@property_bp.route("/leases/<int:lease_id>/terminate", methods=["POST"])
@login_required
@role_required("Landlord")
def terminate_lease(lease_id):
    lease = Lease.query.get_or_404(lease_id)
    lease.active_status = False
    lease.end_date = date.today()
    lease.unit.status = "Vacant"
    db.session.commit()
    flash(f"Lease {lease_id} terminated. Unit {lease.unit.unit_number} is now vacant.", "success")
    return redirect(url_for("property.list_leases"))


# ---------------------------------------------------------------------------
# Tenant management (add tenant user) — Caretaker / Landlord
# ---------------------------------------------------------------------------
@property_bp.route("/tenants/add", methods=["GET", "POST"])
@login_required
@role_required("Landlord", "Caretaker")
def add_tenant():
    import bcrypt as _bcrypt

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if User.query.filter_by(email=email).first():
            flash("A user with that email already exists.", "danger")
            return render_template("caretaker/add_tenant.html")

        from app.models import Role
        tenant_role = Role.query.filter_by(role_name="Tenant").first()
        if not tenant_role:
            flash("Tenant role not found in database.", "danger")
            return render_template("caretaker/add_tenant.html")

        from flask import current_app
        rounds = current_app.config.get("BCRYPT_LOG_ROUNDS", 12)
        hashed = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(rounds=rounds)).decode()

        user = User(email=email, password_hash=hashed, role_id=tenant_role.role_id)
        db.session.add(user)
        db.session.commit()
        flash(f"Tenant account created for {email}.", "success")
        return redirect(url_for("property.caretaker_dashboard"))

    return render_template("caretaker/add_tenant.html")
