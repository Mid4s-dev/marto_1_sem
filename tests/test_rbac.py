"""
TC-SEC-02 — Role-Based Access Control Tests
Validates:
  - Unauthenticated requests redirect to login
  - Wrong role receives HTTP 403 Forbidden
  - Correct role can access its own endpoints
"""
import pytest
from tests.conftest import login, logout


# ---------------------------------------------------------------------------
# Landlord-only endpoints
# ---------------------------------------------------------------------------
LANDLORD_ONLY_ENDPOINTS = [
    "/property/units/add",
    "/finance/arrears",
    "/finance/payments",
    "/audit/logs",
]

# ---------------------------------------------------------------------------
# Caretaker-accessible endpoints
# ---------------------------------------------------------------------------
CARETAKER_ENDPOINTS = [
    "/property/caretaker",
    "/finance/payments/post",
    "/property/leases/assign",
]

# ---------------------------------------------------------------------------
# Tenant-only endpoints
# ---------------------------------------------------------------------------
TENANT_ENDPOINTS = [
    "/finance/statement",
]


class TestUnauthenticatedRedirects:
    def test_unauthenticated_landlord_endpoint_redirects(self, client):
        logout(client)
        resp = client.get("/property/landlord", follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_unauthenticated_audit_log_redirects(self, client):
        logout(client)
        resp = client.get("/audit/logs", follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_unauthenticated_tenant_statement_redirects(self, client):
        logout(client)
        resp = client.get("/finance/statement", follow_redirects=False)
        assert resp.status_code in (302, 401)


class TestLandlordAccess:
    def setup_method(self, method):
        pass  # login done per test

    def test_landlord_can_access_dashboard(self, client):
        logout(client)
        login(client, "landlord@test.com", "AdminPass2026!")
        resp = client.get("/property/landlord", follow_redirects=True)
        assert resp.status_code == 200

    def test_landlord_can_access_audit_logs(self, client):
        logout(client)
        login(client, "landlord@test.com", "AdminPass2026!")
        resp = client.get("/audit/logs", follow_redirects=True)
        assert resp.status_code == 200

    def test_landlord_can_access_arrears(self, client):
        logout(client)
        login(client, "landlord@test.com", "AdminPass2026!")
        resp = client.get("/finance/arrears", follow_redirects=True)
        assert resp.status_code == 200


class TestCaretakerForbiddenRoutes:
    def test_caretaker_cannot_access_audit_logs(self, client):
        logout(client)
        login(client, "caretaker@test.com", "Caretaker2026!")
        resp = client.get("/audit/logs", follow_redirects=True)
        assert resp.status_code == 403

    def test_caretaker_cannot_access_landlord_dashboard(self, client):
        logout(client)
        login(client, "caretaker@test.com", "Caretaker2026!")
        resp = client.get("/property/landlord", follow_redirects=True)
        assert resp.status_code == 403

    def test_caretaker_cannot_add_unit(self, client):
        logout(client)
        login(client, "caretaker@test.com", "Caretaker2026!")
        resp = client.get("/property/units/add", follow_redirects=True)
        assert resp.status_code == 403

    def test_caretaker_can_access_own_dashboard(self, client):
        logout(client)
        login(client, "caretaker@test.com", "Caretaker2026!")
        resp = client.get("/property/caretaker", follow_redirects=True)
        assert resp.status_code == 200


class TestTenantForbiddenRoutes:
    def test_tenant_cannot_access_landlord_dashboard(self, client):
        logout(client)
        login(client, "tenant@test.com", "TenantPass2026!")
        resp = client.get("/property/landlord", follow_redirects=True)
        assert resp.status_code == 403

    def test_tenant_cannot_access_audit_logs(self, client):
        logout(client)
        login(client, "tenant@test.com", "TenantPass2026!")
        resp = client.get("/audit/logs", follow_redirects=True)
        assert resp.status_code == 403

    def test_tenant_cannot_post_payment(self, client):
        logout(client)
        login(client, "tenant@test.com", "TenantPass2026!")
        resp = client.get("/finance/payments/post", follow_redirects=True)
        assert resp.status_code == 403

    def test_tenant_can_access_own_statement(self, client):
        logout(client)
        login(client, "tenant@test.com", "TenantPass2026!")
        resp = client.get("/finance/statement", follow_redirects=True)
        assert resp.status_code == 200
