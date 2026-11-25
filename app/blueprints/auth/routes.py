"""
Auth blueprint — login, logout, account lockout (5-attempt / 30-min).
Passwords are verified with Bcrypt (cost factor 12).
"""
from datetime import datetime, timedelta
from functools import wraps

import bcrypt
from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, current_app, abort,
)
from flask_login import login_user, logout_user, login_required, current_user

from app.models import db, User

auth_bp = Blueprint("auth", __name__, template_folder="../../templates/auth")


# ---------------------------------------------------------------------------
# RBAC decorator
# ---------------------------------------------------------------------------
def role_required(*roles):
    """Decorator that restricts a view to the given role names."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role_name not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _hash_password(plain: str) -> str:
    rounds = current_app.config.get("BCRYPT_LOG_ROUNDS", 12)
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=rounds)).decode()


def _check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _is_account_locked(user: User) -> bool:
    if user.is_locked:
        if user.lock_expiry and datetime.utcnow() > user.lock_expiry:
            # Lockout period expired — auto-unlock
            user.is_locked = False
            user.failed_attempts = 0
            user.lock_expiry = None
            db.session.commit()
            return False
        return True
    return False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        # Check lockout
        if _is_account_locked(user):
            remaining = int((user.lock_expiry - datetime.utcnow()).total_seconds() // 60)
            flash(f"Account locked. Try again in {remaining} minute(s).", "danger")
            return render_template("login.html")

        # Verify password
        if _check_password(password, user.password_hash):
            user.failed_attempts = 0
            user.is_locked = False
            user.lock_expiry = None
            db.session.commit()
            login_user(user, remember=False)
            return _redirect_by_role(user)
        else:
            max_attempts = current_app.config.get("LOCKOUT_ATTEMPTS", 5)
            lockout_mins = current_app.config.get("LOCKOUT_TIME_MINUTES", 30)
            user.failed_attempts += 1

            if user.failed_attempts >= max_attempts:
                user.is_locked = True
                user.lock_expiry = datetime.utcnow() + timedelta(minutes=lockout_mins)
                db.session.commit()
                flash(f"Too many failed attempts. Account locked for {lockout_mins} minutes.", "danger")
            else:
                remaining_tries = max_attempts - user.failed_attempts
                db.session.commit()
                flash(f"Invalid password. {remaining_tries} attempt(s) remaining.", "danger")

            return render_template("login.html")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/access-denied")
def access_denied():
    return render_template("access_denied.html"), 403


# ---------------------------------------------------------------------------
# Role-based redirect helper
# ---------------------------------------------------------------------------
def _redirect_by_role(user: User):
    role = user.role_name
    if role == "Landlord":
        return redirect(url_for("property.landlord_dashboard"))
    elif role == "Caretaker":
        return redirect(url_for("property.caretaker_dashboard"))
    elif role == "Tenant":
        return redirect(url_for("finance.tenant_statement"))
    return redirect(url_for("auth.login"))


# ---------------------------------------------------------------------------
# 403 handler
# ---------------------------------------------------------------------------
from flask import Blueprint as _BP  # noqa


@auth_bp.app_errorhandler(403)
def forbidden(e):
    return render_template("access_denied.html"), 403
