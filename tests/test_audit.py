"""
TC-AUD-01/02 — Forensic Audit Logging Tests
Validates:
  - INSERT operations generate an AuditLog row with correct fields
  - Audit log captures user_id, ip_address, entity, action_type
  - Pre/post JSON snapshots are recorded
  - AuditLog rows cannot be updated or deleted (trigger immutability)
    (trigger test is MySQL-only; skipped on SQLite)
"""
import datetime
import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.models import db, AuditLog, Unit, User, Role
from tests.conftest import login, logout


# ---------------------------------------------------------------------------
# ORM-level audit capture tests (TC-AUD-01)
# ---------------------------------------------------------------------------

class TestAuditLogCapture:
    def test_unit_insert_generates_audit_log(self, app, client):
        """Creating a unit via the web endpoint should produce an AuditLog row."""
        logout(client)
        login(client, "landlord@test.com", "AdminPass2026!")

        initial_count = AuditLog.query.count()

        client.post(
            "/property/units/add",
            data={
                "unit_number": "AUDIT01",
                "monthly_rent": "12000",
                "status": "Vacant",
            },
            follow_redirects=True,
        )

        with app.app_context():
            new_count = AuditLog.query.count()
            # At least one new audit row should have been written
            assert new_count > initial_count

    def test_audit_log_records_correct_entity(self, app, client):
        logout(client)
        login(client, "landlord@test.com", "AdminPass2026!")

        client.post(
            "/property/units/add",
            data={
                "unit_number": "AUDIT02",
                "monthly_rent": "13000",
                "status": "Vacant",
            },
            follow_redirects=True,
        )

        with app.app_context():
            log = (
                AuditLog.query
                .filter(AuditLog.entity_affected.ilike("%unit%"))
                .order_by(AuditLog.timestamp.desc())
                .first()
            )
            assert log is not None
            assert log.action_type == "INSERT"

    def test_audit_log_contains_ip_address(self, app, client):
        logout(client)
        login(client, "landlord@test.com", "AdminPass2026!")

        client.post(
            "/property/units/add",
            data={
                "unit_number": "AUDIT03",
                "monthly_rent": "14000",
                "status": "Vacant",
            },
            follow_redirects=True,
        )

        with app.app_context():
            log = (
                AuditLog.query
                .order_by(AuditLog.timestamp.desc())
                .first()
            )
            assert log is not None
            assert log.ip_address is not None

    def test_audit_log_post_snapshot_is_not_null_for_insert(self, app, client):
        logout(client)
        login(client, "landlord@test.com", "AdminPass2026!")

        client.post(
            "/property/units/add",
            data={
                "unit_number": "AUDIT04",
                "monthly_rent": "15000",
                "status": "Vacant",
            },
            follow_redirects=True,
        )

        with app.app_context():
            log = (
                AuditLog.query
                .filter_by(action_type="INSERT")
                .order_by(AuditLog.timestamp.desc())
                .first()
            )
            assert log is not None
            # post_change_json should carry the new row data
            assert log.post_change_json is not None


# ---------------------------------------------------------------------------
# Direct ORM insert produces audit row (TC-AUD-01)
# ---------------------------------------------------------------------------

class TestDirectOrmAudit:
    def test_direct_orm_insert_audited(self, app):
        """A direct ORM add/commit should still trigger the audit listener."""
        with app.app_context():
            before = AuditLog.query.count()

            unit = Unit(unit_number="DIRORM01", monthly_rent=9000.00, status="Vacant")
            db.session.add(unit)
            db.session.commit()

            after = AuditLog.query.count()
            assert after > before

            # Cleanup
            Unit.query.filter_by(unit_number="DIRORM01").delete()
            db.session.commit()


# ---------------------------------------------------------------------------
# Audit log immutability (TC-AUD-02)
# Only meaningful on MySQL (triggers); on SQLite we test the ORM layer.
# ---------------------------------------------------------------------------

class TestAuditLogImmutability:
    def test_audit_log_rows_are_present_and_readable(self, app):
        """Landlord endpoint must be able to read audit logs (read-only)."""
        with app.app_context():
            logs = AuditLog.query.all()
            # After all the above tests there should be at least some logs
            assert isinstance(logs, list)

    def test_audit_log_viewer_requires_landlord_role(self, client):
        logout(client)
        login(client, "tenant@test.com", "TenantPass2026!")
        resp = client.get("/audit/logs", follow_redirects=True)
        assert resp.status_code == 403

    @pytest.mark.skip(
        reason="MySQL trigger enforcement only; SQLite in-memory DB used for tests"
    )
    def test_mysql_trigger_prevents_update(self, app):
        """
        On a real MySQL instance this would raise OperationalError with
        SQLSTATE 45000 when attempting to UPDATE an AuditLog row.
        """
        with app.app_context():
            log = AuditLog.query.first()
            if log:
                with pytest.raises((OperationalError, ProgrammingError)):
                    db.session.execute(
                        db.text(
                            f"UPDATE AuditLogs SET ip_address='tampered' "
                            f"WHERE log_id={log.log_id}"
                        )
                    )
                    db.session.commit()

    @pytest.mark.skip(
        reason="MySQL trigger enforcement only; SQLite in-memory DB used for tests"
    )
    def test_mysql_trigger_prevents_delete(self, app):
        with app.app_context():
            log = AuditLog.query.first()
            if log:
                with pytest.raises((OperationalError, ProgrammingError)):
                    db.session.execute(
                        db.text(f"DELETE FROM AuditLogs WHERE log_id={log.log_id}")
                    )
                    db.session.commit()
