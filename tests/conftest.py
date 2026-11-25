"""
Pytest fixtures — shared test infrastructure.
Uses SQLite in-memory DB so no MySQL server is needed for tests.
"""
import pytest
import bcrypt

from app import create_app
from app.models import db as _db, Role, User, Unit, Lease, Charge, Payment


@pytest.fixture(scope="session")
def app():
    """Create the Flask test application (SQLite in-memory)."""
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        _seed_roles_and_users()
        yield application
        _db.drop_all()


@pytest.fixture(scope="session")
def db(app):
    return _db


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=4)).decode()


def _seed_roles_and_users():
    """Seed roles and three default users into the test DB."""
    landlord_role  = Role(role_name="Landlord",  permissions_mask="all")
    caretaker_role = Role(role_name="Caretaker", permissions_mask="units:rw")
    tenant_role    = Role(role_name="Tenant",     permissions_mask="statement:r")
    _db.session.add_all([landlord_role, caretaker_role, tenant_role])
    _db.session.flush()

    users = [
        User(email="landlord@test.com",  password_hash=_hash("AdminPass2026!"),    role_id=landlord_role.role_id),
        User(email="caretaker@test.com", password_hash=_hash("Caretaker2026!"),    role_id=caretaker_role.role_id),
        User(email="tenant@test.com",    password_hash=_hash("TenantPass2026!"),   role_id=tenant_role.role_id),
    ]
    _db.session.add_all(users)
    _db.session.commit()


def login(client, email: str, password: str):
    """Helper to POST login form and return the response."""
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def logout(client):
    return client.get("/auth/logout", follow_redirects=True)
