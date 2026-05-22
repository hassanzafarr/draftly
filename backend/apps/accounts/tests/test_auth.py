"""Auth + multi-tenancy smoke tests.

Covers the full auth path (register → login → /me) plus the critical
multi-tenant isolation invariant enforced by `IsOrgMember` and queryset
scoping in document views.
"""
import pytest

from apps.accounts.models import Organization, User

pytestmark = pytest.mark.django_db


def test_register_creates_user_and_org(api_client):
    payload = {
        "org_name": "Acme Corp",
        "email": "founder@acme.test",
        "password": "StrongPass123!",
    }

    res = api_client.post("/api/auth/register/", payload, format="json")

    assert res.status_code == 201, res.content
    body = res.json()
    assert body["email"] == "founder@acme.test"
    assert body["role"] == User.Role.ADMIN

    org = Organization.objects.get(name="Acme Corp")
    user = User.objects.get(email="founder@acme.test")
    assert user.org_id == org.id
    assert user.role == User.Role.ADMIN
    assert user.check_password("StrongPass123!")


def test_login_returns_jwt_pair(api_client, user):
    res = api_client.post(
        "/api/auth/token/",
        {"email": user.email, "password": user._raw_password},
        format="json",
    )

    assert res.status_code == 200, res.content
    body = res.json()
    assert "access" in body
    assert "refresh" in body
    assert body["access"] and body["refresh"]


def test_me_returns_user_with_nested_org(auth_client):
    res = auth_client.get("/api/auth/me/")

    assert res.status_code == 200, res.content
    body = res.json()
    assert body["email"] == auth_client.user.email
    assert body["role"] == auth_client.user.role
    assert body["org"]["id"] == str(auth_client.user.org.id)
    assert body["org"]["subscription_tier"] == "free"
    assert body["org"]["doc_quota"] == 10
    assert body["org"]["proposal_quota"] == 3
    assert body["org"]["seat_limit"] == 1
    assert body["org"]["billing_cadence"] == "monthly"
    assert body["org"]["proposal_pack_balance"] == 0


def test_org_isolation_blocks_cross_tenant_document_reads(
    auth_client, other_auth_client, user, other_user
):
    """User in Org B must not see documents owned by Org A."""
    from apps.documents.tests.factories import DocumentFactory

    DocumentFactory(org=user.org, uploaded_by=user, title="Org A secret doc")
    DocumentFactory(org=other_user.org, uploaded_by=other_user, title="Org B own doc")

    res_a = auth_client.get("/api/documents/")
    res_b = other_auth_client.get("/api/documents/")

    assert res_a.status_code == 200
    assert res_b.status_code == 200

    titles_a = {d["title"] for d in res_a.json()}
    titles_b = {d["title"] for d in res_b.json()}

    assert titles_a == {"Org A secret doc"}
    assert titles_b == {"Org B own doc"}
    assert "Org A secret doc" not in titles_b
    assert "Org B own doc" not in titles_a
