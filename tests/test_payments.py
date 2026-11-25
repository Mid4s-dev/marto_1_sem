"""
TC-DB-01 — Payment Processing & M-Pesa Validation Tests
Validates:
  - Valid M-Pesa codes (^[A-Z0-9]{10}$) are accepted
  - Invalid codes (wrong length, lowercase, special chars) are rejected
  - Duplicate M-Pesa code raises IntegrityError and is rejected
  - Dynamic balance formula: balance = total_charges - total_payments
"""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models import db, Unit, Lease, Charge, Payment, User, Role
from tests.conftest import login, logout

import datetime


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def demo_lease(app):
    """Create a unit, lease, and initial charge for payment tests."""
    with app.app_context():
        tenant = User.query.filter_by(email="tenant@test.com").first()
        unit = Unit(unit_number="T01", monthly_rent=15000.00, status="Vacant")
        db.session.add(unit)
        db.session.flush()

        lease = Lease(
            tenant_user_id=tenant.user_id,
            unit_id=unit.unit_id,
            start_date=datetime.date.today(),
            active_status=True,
        )
        db.session.add(lease)
        db.session.flush()

        charge = Charge(
            lease_id=lease.lease_id,
            charge_type="Monthly Rent",
            amount=15000.00,
            due_date=datetime.date.today(),
        )
        db.session.add(charge)
        db.session.commit()

        yield lease.lease_id

        # Cleanup
        Payment.query.filter_by(lease_id=lease.lease_id).delete()
        Charge.query.filter_by(lease_id=lease.lease_id).delete()
        db.session.delete(lease)
        db.session.delete(unit)
        db.session.commit()


# ---------------------------------------------------------------------------
# M-Pesa regex validation via the POST endpoint
# ---------------------------------------------------------------------------

VALID_CODES = ["QA12BC34EF", "ABCDE12345", "1234567890", "ZZZZZZZZZZ"]
INVALID_CODES = [
    "short",          # too short
    "TOOLONGCODE1",   # too long
    "qa12bc34ef",     # lowercase
    "QA12BC34E!",     # special character
    "QA12 BC34E",     # space
    "",               # empty
]


class TestMpesaRegex:
    def test_valid_codes_accepted_by_endpoint(self, client, app, demo_lease):
        logout(client)
        login(client, "caretaker@test.com", "Caretaker2026!")

        for code in VALID_CODES:
            resp = client.post(
                "/finance/payments/post",
                data={
                    "lease_id": demo_lease,
                    "amount": "1000",
                    "mpesa_code": code,
                },
                follow_redirects=True,
            )
            # Should succeed (200 with success flash) or at least not show regex error
            assert b"Invalid M-Pesa" not in resp.data, f"Code {code} should be valid"

            # Clean up so next code doesn't hit duplicate constraint
            with app.app_context():
                p = Payment.query.filter_by(mpesa_code=code).first()
                if p:
                    db.session.delete(p)
                    db.session.commit()

    def test_invalid_codes_rejected_by_endpoint(self, client, demo_lease):
        logout(client)
        login(client, "caretaker@test.com", "Caretaker2026!")

        for code in INVALID_CODES:
            resp = client.post(
                "/finance/payments/post",
                data={
                    "lease_id": demo_lease,
                    "amount": "1000",
                    "mpesa_code": code,
                },
                follow_redirects=True,
            )
            assert b"Invalid M-Pesa" in resp.data, f"Code '{code}' should be invalid"


# ---------------------------------------------------------------------------
# Duplicate M-Pesa code prevention
# ---------------------------------------------------------------------------

class TestDuplicateMpesaPrevention:
    def test_duplicate_mpesa_code_rejected(self, client, app, demo_lease):
        """TC-DB-01: posting the same M-Pesa code twice must be rejected."""
        logout(client)
        login(client, "caretaker@test.com", "Caretaker2026!")

        code = "DUPL000001"

        # First payment — must succeed
        resp1 = client.post(
            "/finance/payments/post",
            data={"lease_id": demo_lease, "amount": "5000", "mpesa_code": code},
            follow_redirects=True,
        )
        assert b"posted successfully" in resp1.data

        # Second payment with same code — must be rejected
        resp2 = client.post(
            "/finance/payments/post",
            data={"lease_id": demo_lease, "amount": "5000", "mpesa_code": code},
            follow_redirects=True,
        )
        assert b"Duplicate" in resp2.data or b"already been recorded" in resp2.data

        # Cleanup
        with app.app_context():
            Payment.query.filter_by(mpesa_code=code).delete()
            db.session.commit()

    def test_duplicate_at_orm_level_raises_integrity_error(self, app, demo_lease):
        """Direct ORM insert of duplicate mpesa_code must raise IntegrityError."""
        with app.app_context():
            lease = Lease.query.get(demo_lease)
            p1 = Payment(lease_id=lease.lease_id, amount=1000, mpesa_code="ORMDUP0001")
            p2 = Payment(lease_id=lease.lease_id, amount=1000, mpesa_code="ORMDUP0001")
            db.session.add(p1)
            db.session.commit()

            with pytest.raises(IntegrityError):
                db.session.add(p2)
                db.session.commit()

            db.session.rollback()
            Payment.query.filter_by(mpesa_code="ORMDUP0001").delete()
            db.session.commit()


# ---------------------------------------------------------------------------
# Dynamic balance formula
# ---------------------------------------------------------------------------

class TestDynamicBalance:
    def test_balance_equals_charges_minus_payments(self, app, demo_lease):
        """FR-3.3: balance = Σcharges − Σpayments (never stored statically)."""
        with app.app_context():
            lease = Lease.query.get(demo_lease)

            # Initial balance should equal the charge amount (15 000)
            assert lease.balance == pytest.approx(15000.00, abs=0.01)

            # Add a partial payment of 10 000
            payment = Payment(
                lease_id=lease.lease_id,
                amount=10000.00,
                mpesa_code="BALTEST001",
            )
            db.session.add(payment)
            db.session.commit()

            lease = Lease.query.get(demo_lease)
            assert lease.balance == pytest.approx(5000.00, abs=0.01)

            # Add another charge
            extra = Charge(
                lease_id=lease.lease_id,
                charge_type="Water",
                amount=500.00,
                due_date=datetime.date.today(),
            )
            db.session.add(extra)
            db.session.commit()

            lease = Lease.query.get(demo_lease)
            assert lease.balance == pytest.approx(5500.00, abs=0.01)

            # Cleanup
            Payment.query.filter_by(mpesa_code="BALTEST001").delete()
            Charge.query.filter_by(charge_type="Water", lease_id=lease.lease_id).delete()
            db.session.commit()

    def test_fully_paid_lease_has_zero_balance(self, app, demo_lease):
        with app.app_context():
            lease = Lease.query.get(demo_lease)
            payment = Payment(
                lease_id=lease.lease_id,
                amount=15000.00,
                mpesa_code="FULLPAY001",
            )
            db.session.add(payment)
            db.session.commit()

            lease = Lease.query.get(demo_lease)
            assert lease.balance == pytest.approx(0.00, abs=0.01)

            Payment.query.filter_by(mpesa_code="FULLPAY001").delete()
            db.session.commit()
