"""GDPR endpoint tests: data export (access/portability) and account erasure."""

import io
import json
import zipfile

import pytest
import stripe
from django.core.files.storage import default_storage
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Organization, User
from apps.accounts.tests.factories import OrganizationFactory, UserFactory
from apps.documents.models import Chunk, Document
from apps.documents.tests.factories import DocumentFactory
from apps.proposals.models import RFP, Proposal
from apps.proposals.tests.factories import ProposalFactory

pytestmark = pytest.mark.django_db

EXPORT_URL = "/api/auth/account/export/"
DELETE_URL = "/api/auth/account/delete/"
PASSWORD = "TestPass123!"


def _client_for(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


def _read_export(res):
    archive = zipfile.ZipFile(io.BytesIO(b"".join(res.streaming_content)))
    return archive, json.loads(archive.read("data.json"))


def _add_chunk(doc):
    return Chunk.objects.create(
        document=doc, org=doc.org, content="chunk", embedding=[0.0] * 768, metadata={}
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def test_export_requires_auth(api_client):
    assert api_client.get(EXPORT_URL).status_code == 401


def test_export_contains_org_data_and_files(auth_client, user):
    DocumentFactory(org=user.org, uploaded_by=user, title="Capabilities")
    proposal = ProposalFactory(rfp__org=user.org, rfp__created_by=user)

    res = auth_client.get(EXPORT_URL)

    assert res.status_code == 200
    assert res["Content-Type"] == "application/zip"
    assert "attachment" in res["Content-Disposition"]

    archive, data = _read_export(res)
    assert data["user"]["email"] == user.email
    assert data["organization"]["id"] == str(user.org.id)
    assert [m["email"] for m in data["members"]] == [user.email]

    [exported_doc] = data["documents"]
    assert exported_doc["title"] == "Capabilities"
    assert exported_doc["uploaded_by"] == user.email
    assert archive.read(exported_doc["file"]) == b"test content"

    [exported_rfp] = data["rfps"]
    assert exported_rfp["raw_text"] == proposal.rfp.raw_text
    [exported_proposal] = data["proposals"]
    assert exported_proposal["id"] == str(proposal.id)
    assert exported_proposal["sections"] == proposal.sections


def test_export_excludes_other_orgs_data(auth_client, other_user):
    DocumentFactory(org=other_user.org, uploaded_by=other_user, title="Secret")
    ProposalFactory(rfp__org=other_user.org, rfp__created_by=other_user)

    _, data = _read_export(auth_client.get(EXPORT_URL))

    assert data["documents"] == []
    assert data["rfps"] == []
    assert data["proposals"] == []
    assert other_user.email not in [m["email"] for m in data["members"]]


def test_export_tolerates_missing_stored_file(auth_client, user):
    doc = DocumentFactory(org=user.org, uploaded_by=user)
    default_storage.delete(doc.file.name)

    res = auth_client.get(EXPORT_URL)

    assert res.status_code == 200
    _, data = _read_export(res)
    assert data["documents"][0]["file"] is None


# ---------------------------------------------------------------------------
# Erasure — re-authentication and guards
# ---------------------------------------------------------------------------


def test_delete_requires_auth(api_client):
    assert api_client.post(DELETE_URL, {"password": PASSWORD}).status_code == 401


def test_delete_rejects_wrong_password(auth_client, user):
    res = auth_client.post(DELETE_URL, {"password": "wrong"}, format="json")

    assert res.status_code == 400
    assert User.objects.filter(pk=user.pk).exists()


def test_google_only_account_must_confirm_email(org):
    google_user = UserFactory(org=org, google_id="g-123")
    google_user.set_unusable_password()
    google_user.save()
    client = _client_for(google_user)

    bad = client.post(DELETE_URL, {"confirm_email": "nope@example.com"}, format="json")
    assert bad.status_code == 400
    assert User.objects.filter(pk=google_user.pk).exists()

    ok = client.post(DELETE_URL, {"confirm_email": google_user.email.upper()}, format="json")
    assert ok.status_code == 200
    assert not User.objects.filter(pk=google_user.pk).exists()


def test_demo_account_cannot_be_deleted():
    demo_user = UserFactory(org=OrganizationFactory(subscription_tier=Organization.Tier.DEMO))

    res = _client_for(demo_user).post(DELETE_URL, {"password": PASSWORD}, format="json")

    assert res.status_code == 403
    assert User.objects.filter(pk=demo_user.pk).exists()


# ---------------------------------------------------------------------------
# Erasure — organization scope (sole member)
# ---------------------------------------------------------------------------


def test_sole_member_delete_erases_org_content_and_files(
    auth_client, user, other_user, mailoutbox, django_capture_on_commit_callbacks
):
    org_id = user.org_id
    doc = DocumentFactory(org=user.org, uploaded_by=user)
    _add_chunk(doc)
    ProposalFactory(rfp__org=user.org, rfp__created_by=user)
    other_doc = DocumentFactory(org=other_user.org, uploaded_by=other_user)
    file_name = doc.file.name
    assert default_storage.exists(file_name)

    with django_capture_on_commit_callbacks(execute=True):
        res = auth_client.post(DELETE_URL, {"password": PASSWORD}, format="json")

    assert res.status_code == 200, res.content
    assert res.json()["scope"] == "organization"
    assert not Organization.objects.filter(pk=org_id).exists()
    assert not User.objects.filter(pk=user.pk).exists()
    assert not Document.objects.filter(org_id=org_id).exists()
    assert not Chunk.objects.filter(org_id=org_id).exists()
    assert not RFP.objects.filter(org_id=org_id).exists()
    assert not Proposal.objects.filter(org_id=org_id).exists()
    assert not default_storage.exists(file_name)

    # Other tenants are untouched.
    assert Document.objects.filter(pk=other_doc.pk).exists()
    assert default_storage.exists(other_doc.file.name)

    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [user.email]


def test_old_token_rejected_after_deletion(auth_client):
    auth_client.post(DELETE_URL, {"password": PASSWORD}, format="json")

    assert auth_client.get("/api/auth/me/").status_code == 401


def test_stripe_customer_deleted_before_org(auth_client, user, settings, monkeypatch):
    settings.STRIPE_SECRET_KEY = "sk_test_dummy"
    user.org.stripe_customer_id = "cus_123"
    user.org.save()
    deleted = []
    monkeypatch.setattr(stripe.Customer, "delete", lambda cid: deleted.append(cid))

    res = auth_client.post(DELETE_URL, {"password": PASSWORD}, format="json")

    assert res.status_code == 200
    assert deleted == ["cus_123"]


def test_stripe_failure_aborts_erasure(auth_client, user, settings, monkeypatch):
    settings.STRIPE_SECRET_KEY = "sk_test_dummy"
    user.org.stripe_customer_id = "cus_123"
    user.org.save()

    def _boom(cid):
        raise stripe.APIConnectionError("network down")

    monkeypatch.setattr(stripe.Customer, "delete", _boom)

    res = auth_client.post(DELETE_URL, {"password": PASSWORD}, format="json")

    assert res.status_code == 502
    assert Organization.objects.filter(pk=user.org_id).exists()
    assert User.objects.filter(pk=user.pk).exists()


def test_already_deleted_stripe_customer_does_not_block(auth_client, user, settings, monkeypatch):
    settings.STRIPE_SECRET_KEY = "sk_test_dummy"
    user.org.stripe_customer_id = "cus_gone"
    user.org.save()

    def _missing(cid):
        raise stripe.InvalidRequestError("No such customer", "id", code="resource_missing")

    monkeypatch.setattr(stripe.Customer, "delete", _missing)

    res = auth_client.post(DELETE_URL, {"password": PASSWORD}, format="json")

    assert res.status_code == 200
    assert not Organization.objects.filter(pk=user.org_id).exists()


# ---------------------------------------------------------------------------
# Erasure — user scope (org has other members)
# ---------------------------------------------------------------------------


@pytest.fixture
def studio_org():
    return OrganizationFactory(subscription_tier=Organization.Tier.STUDIO)


def test_last_admin_delete_promotes_earliest_member(studio_org):
    admin = UserFactory(org=studio_org, role=User.Role.ADMIN)
    first_member = UserFactory(org=studio_org, role=User.Role.MEMBER)
    UserFactory(org=studio_org, role=User.Role.MEMBER)
    doc = DocumentFactory(org=studio_org, uploaded_by=admin)

    res = _client_for(admin).post(DELETE_URL, {"password": PASSWORD}, format="json")

    assert res.status_code == 200
    assert res.json()["scope"] == "user"
    assert not User.objects.filter(pk=admin.pk).exists()
    assert Organization.objects.filter(pk=studio_org.pk).exists()
    first_member.refresh_from_db()
    assert first_member.role == User.Role.ADMIN
    # Org content survives with its author detached.
    doc.refresh_from_db()
    assert doc.uploaded_by is None


def test_member_delete_leaves_roles_unchanged(studio_org):
    admin = UserFactory(org=studio_org, role=User.Role.ADMIN)
    member = UserFactory(org=studio_org, role=User.Role.MEMBER)
    bystander = UserFactory(org=studio_org, role=User.Role.MEMBER)

    res = _client_for(member).post(DELETE_URL, {"password": PASSWORD}, format="json")

    assert res.status_code == 200
    assert not User.objects.filter(pk=member.pk).exists()
    admin.refresh_from_db()
    bystander.refresh_from_db()
    assert admin.role == User.Role.ADMIN
    assert bystander.role == User.Role.MEMBER
