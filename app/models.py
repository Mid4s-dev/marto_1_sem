"""
SQLAlchemy ORM models — 3NF relational schema.
All tables match the ER diagram in the README.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
class Role(db.Model):
    __tablename__ = "Roles"

    role_id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)
    permissions_mask = db.Column(db.String(255), nullable=True)

    users = db.relationship("User", back_populates="role", lazy="dynamic")

    def __repr__(self):
        return f"<Role {self.role_name}>"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "Users"

    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("Roles.role_id"), nullable=False)
    failed_attempts = db.Column(db.Integer, default=0, nullable=False)
    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    lock_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    role = db.relationship("Role", back_populates="users")
    leases = db.relationship("Lease", back_populates="tenant", foreign_keys="Lease.tenant_user_id", lazy="dynamic")
    verified_payments = db.relationship("Payment", back_populates="verified_by", foreign_keys="Payment.verified_by_user_id", lazy="dynamic")
    audit_logs = db.relationship("AuditLog", back_populates="user", lazy="dynamic")

    # Flask-Login requires get_id() to return a string
    def get_id(self):
        return str(self.user_id)

    @property
    def role_name(self):
        return self.role.role_name if self.role else None

    def __repr__(self):
        return f"<User {self.email}>"


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------
class Unit(db.Model):
    __tablename__ = "Units"

    unit_id = db.Column(db.Integer, primary_key=True)
    unit_number = db.Column(db.String(20), unique=True, nullable=False)
    monthly_rent = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(
        db.Enum("Vacant", "Occupied", "Maintenance", name="unit_status"),
        default="Vacant",
        nullable=False,
    )
    deposit = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    description = db.Column(db.String(500), default="", nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    bedrooms = db.Column(db.Integer, default=1, nullable=False)
    bathrooms = db.Column(db.Integer, default=1, nullable=False)

    leases = db.relationship("Lease", back_populates="unit", lazy="dynamic")

    def __repr__(self):
        return f"<Unit {self.unit_number} [{self.status}]>"


# ---------------------------------------------------------------------------
# Leases
# ---------------------------------------------------------------------------
class Lease(db.Model):
    __tablename__ = "Leases"

    lease_id = db.Column(db.Integer, primary_key=True)
    tenant_user_id = db.Column(db.Integer, db.ForeignKey("Users.user_id"), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey("Units.unit_id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    active_status = db.Column(db.Boolean, default=True, nullable=False)

    tenant = db.relationship("User", back_populates="leases", foreign_keys=[tenant_user_id])
    unit = db.relationship("Unit", back_populates="leases")
    charges = db.relationship("Charge", back_populates="lease", lazy="dynamic", cascade="all, delete-orphan")
    payments = db.relationship("Payment", back_populates="lease", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def balance(self):
        """Dynamic balance: total charges minus total payments."""
        total_charges = sum(c.amount for c in self.charges)
        total_payments = sum(p.amount for p in self.payments)
        return float(total_charges) - float(total_payments)

    def __repr__(self):
        return f"<Lease {self.lease_id} tenant={self.tenant_user_id} unit={self.unit_id}>"


# ---------------------------------------------------------------------------
# Charges
# ---------------------------------------------------------------------------
class Charge(db.Model):
    __tablename__ = "Charges"

    charge_id = db.Column(db.Integer, primary_key=True)
    lease_id = db.Column(db.Integer, db.ForeignKey("Leases.lease_id"), nullable=False)
    charge_type = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    lease = db.relationship("Lease", back_populates="charges")

    def __repr__(self):
        return f"<Charge {self.charge_type} {self.amount}>"


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------
class Payment(db.Model):
    __tablename__ = "Payments"

    payment_id = db.Column(db.Integer, primary_key=True)
    lease_id = db.Column(db.Integer, db.ForeignKey("Leases.lease_id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    mpesa_code = db.Column(db.String(10), unique=True, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    verified_by_user_id = db.Column(db.Integer, db.ForeignKey("Users.user_id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    lease = db.relationship("Lease", back_populates="payments")
    verified_by = db.relationship("User", back_populates="verified_payments", foreign_keys=[verified_by_user_id])

    def __repr__(self):
        return f"<Payment {self.mpesa_code} {self.amount}>"


# ---------------------------------------------------------------------------
# AuditLogs
# ---------------------------------------------------------------------------
class AuditLog(db.Model):
    __tablename__ = "AuditLogs"

    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("Users.user_id"), nullable=True)
    action_type = db.Column(db.String(50), nullable=False)   # INSERT / UPDATE / DELETE
    entity_affected = db.Column(db.String(100), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    pre_change_json = db.Column(db.JSON, nullable=True)
    post_change_json = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action_type} on {self.entity_affected}:{self.entity_id}>"
