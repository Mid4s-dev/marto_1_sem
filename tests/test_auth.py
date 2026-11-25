"""
TC-SEC-01 — Authentication & Account Lockout Tests
Validates:
  - Bcrypt hashing: plain-text never stored
  - Correct password → successful login
  - Wrong password → 403 / flash message
  - 5 consecutive failures → account locked
  - Locked account → access denied even with correct password
"""
import pytest
import bcrypt

from app.models import db, User
from tests.conftest import login, logout


class TestBcryptHashing:
    def test_password_is_not_stored_as_plain_text(self, app):
        """Plain-text password must not appear anywhere in the Users table."""
        with app.app_context():
            users = User.query.all()
            for user in users:
                assert "AdminPass2026!" not in user.password_hash
                assert "Caretaker2026!" not in user.password_hash
                assert "TenantPass2026!" not in user.password_hash

    def test_password_hash_is_valid_bcrypt(self, app):
        """Stored hash must be a valid bcrypt digest."""
        with app.app_context():
            user = User.query.filter_by(email="landlord@test.com").first()
            assert user is not None
            # bcrypt.checkpw raises ValueError if hash is malformed
            result = bcrypt.checkpw(b"AdminPass2026!", user.password_hash.encode())
            assert result is True

    def test_wrong_password_does_not_match(self, app):
        with app.app_context():
            user = User.query.filter_by(email="landlord@test.com").first()
            result = bcrypt.checkpw(b"WrongPassword!", user.password_hash.encode())
            assert result is False


class TestLoginLogout:
    def test_valid_landlord_login_redirects_to_dashboard(self, client):
        resp = login(client, "landlord@test.com", "AdminPass2026!")
        assert resp.status_code == 200
        assert b"Portfolio Overview" in resp.data or b"Dashboard" in resp.data

    def test_valid_caretaker_login(self, client):
        logout(client)
        resp = login(client, "caretaker@test.com", "Caretaker2026!")
        assert resp.status_code == 200

    def test_valid_tenant_login(self, client):
        logout(client)
        resp = login(client, "tenant@test.com", "TenantPass2026!")
        assert resp.status_code == 200

    def test_invalid_password_shows_error(self, client):
        logout(client)
        resp = login(client, "landlord@test.com", "WrongPassword")
        assert b"Invalid" in resp.data or b"attempt" in resp.data

    def test_unknown_email_shows_error(self, client):
        resp = login(client, "nobody@test.com", "anything")
        assert b"Invalid" in resp.data

    def test_logout_redirects_to_login(self, client):
        login(client, "landlord@test.com", "AdminPass2026!")
        resp = logout(client)
        assert b"logged out" in resp.data or b"Sign In" in resp.data


class TestBruteForceProtection:
    def test_account_locked_after_five_failed_attempts(self, client, app):
        """TC-SEC-01: 6th attempt must be rejected (account locked)."""
        logout(client)
        email = "tenant@test.com"

        # Reset state first
        with app.app_context():
            user = User.query.filter_by(email=email).first()
            user.failed_attempts = 0
            user.is_locked = False
            user.lock_expiry = None
            db.session.commit()

        # 5 bad attempts
        for _ in range(5):
            login(client, email, "BadPassword!")

        # 6th attempt — even with correct password, must be rejected
        resp = login(client, email, "TenantPass2026!")
        assert b"locked" in resp.data.lower() or b"Too many" in resp.data

        # Verify DB state
        with app.app_context():
            user = User.query.filter_by(email=email).first()
            assert user.is_locked is True
            assert user.lock_expiry is not None

    def test_failed_attempts_counter_increments(self, client, app):
        email = "caretaker@test.com"
        with app.app_context():
            user = User.query.filter_by(email=email).first()
            user.failed_attempts = 0
            user.is_locked = False
            user.lock_expiry = None
            db.session.commit()

        login(client, email, "BadPassword!")
        login(client, email, "BadPassword!")

        with app.app_context():
            user = User.query.filter_by(email=email).first()
            assert user.failed_attempts == 2

    def test_successful_login_resets_failed_counter(self, client, app):
        email = "landlord@test.com"
        with app.app_context():
            user = User.query.filter_by(email=email).first()
            user.failed_attempts = 3
            user.is_locked = False
            db.session.commit()

        login(client, email, "AdminPass2026!")

        with app.app_context():
            user = User.query.filter_by(email=email).first()
            assert user.failed_attempts == 0
