"""Team invitation flow tests: invite, seat enforcement, accept, revoke."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Invitation, Organization, User
from apps.accounts.tests.factories import OrganizationFactory, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def studio_org(db):
    """Org with multiple seats (studio = 5)."""
    return OrganizationFactory(subscription_tier=Organization.Tier.STUDIO)


@pytest.fixture
def studio_admin(db, studio_org):
    return UserFactory(org=studio_org, role=User.Role.ADMIN)


@pytest.fixture
def studio_admin_client(api_client, studio_admin):
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(studio_admin)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    api_client.user = studio_admin
    return api_client


def _invite(client, email="newbie@example.com", role="member"):
    return client.post("/api/auth/team/invites/", {"email": email, "role": role}, format="json")


def test_admin_can_invite_and_email_sent(studio_admin_client, studio_org, mailoutbox):
    res = _invite(studio_admin_client)

    assert res.status_code == 201, res.content
    body = res.json()
    assert body["email"] == "newbie@example.com"
    assert body["status"] == Invitation.Status.PENDING

    invite = Invitation.objects.get(org=studio_org, email="newbie@example.com")
    assert len(mailoutbox) == 1
    assert invite.token in mailoutbox[0].body
    assert "/accept-invite?token=" in mailoutbox[0].body


def test_member_cannot_invite(api_client, studio_org):
    from rest_framework_simplejwt.tokens import RefreshToken

    member = UserFactory(org=studio_org, role=User.Role.MEMBER)
    token = RefreshToken.for_user(member)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    res = _invite(api_client)
    assert res.status_code == 403


def test_invite_blocked_at_seat_limit(auth_client):
    """Free tier has 1 seat — the admin occupies it, so any invite is blocked."""
    res = _invite(auth_client)

    assert res.status_code == 403
    assert "Seat limit reached" in res.json()["detail"]


def test_duplicate_pending_invite_blocked(studio_admin_client):
    assert _invite(studio_admin_client).status_code == 201
    res = _invite(studio_admin_client)

    assert res.status_code == 400
    assert "already pending" in res.json()["detail"]


def test_expired_invites_do_not_block_or_show_as_pending(studio_admin_client):
    assert _invite(studio_admin_client, email="old@example.com").status_code == 201
    invite = Invitation.objects.get(email="old@example.com")
    invite.expires_at = timezone.now() - timedelta(minutes=1)
    invite.save(update_fields=["expires_at"])

    list_res = studio_admin_client.get("/api/auth/team/invites/")
    assert list_res.status_code == 200
    assert list_res.json() == []

    reinvite = _invite(studio_admin_client, email="old@example.com")
    assert reinvite.status_code == 201, reinvite.content


def test_invite_existing_user_blocked(studio_admin_client, user):
    res = _invite(studio_admin_client, email=user.email)

    assert res.status_code == 400
    assert "already has a Draftly account" in res.json()["detail"]


def test_accept_invite_creates_active_user_and_logs_in(api_client, studio_admin_client, studio_org):
    _invite(studio_admin_client, email="joiner@example.com")
    invite = Invitation.objects.get(email="joiner@example.com")

    res = api_client.post(
        "/api/auth/invites/accept/",
        {"token": invite.token, "password": "StrongPass123!", "terms_accepted": True},
        format="json",
    )

    assert res.status_code == 201, res.content
    body = res.json()
    assert body["access"] and body["refresh"]
    assert body["user"]["email"] == "joiner@example.com"
    assert body["user"]["org"]["id"] == str(studio_org.id)

    joiner = User.objects.get(email="joiner@example.com")
    assert joiner.is_active is True
    assert joiner.org_id == studio_org.id
    assert joiner.role == User.Role.MEMBER

    invite.refresh_from_db()
    assert invite.status == Invitation.Status.ACCEPTED
    assert invite.accepted_at is not None


def test_accept_expired_invite_rejected(api_client, studio_admin_client):
    _invite(studio_admin_client, email="late@example.com")
    invite = Invitation.objects.get(email="late@example.com")
    invite.expires_at = timezone.now() - timedelta(minutes=1)
    invite.save(update_fields=["expires_at"])

    res = api_client.post(
        "/api/auth/invites/accept/",
        {"token": invite.token, "password": "StrongPass123!", "terms_accepted": True},
        format="json",
    )

    assert res.status_code == 410


def test_revoked_invite_cannot_be_accepted(api_client, studio_admin_client):
    _invite(studio_admin_client, email="gone@example.com")
    invite = Invitation.objects.get(email="gone@example.com")

    revoke = studio_admin_client.delete(f"/api/auth/team/invites/{invite.id}/")
    assert revoke.status_code == 204

    res = api_client.post(
        "/api/auth/invites/accept/",
        {"token": invite.token, "password": "StrongPass123!", "terms_accepted": True},
        format="json",
    )
    assert res.status_code == 410


def test_invite_info_public_endpoint(api_client, studio_admin_client, studio_org):
    _invite(studio_admin_client, email="peek@example.com")
    invite = Invitation.objects.get(email="peek@example.com")

    res = api_client.get(f"/api/auth/invites/{invite.token}/")

    assert res.status_code == 200, res.content
    body = res.json()
    assert body["email"] == "peek@example.com"
    assert body["org_name"] == studio_org.name
    assert body["role"] == "member"


def test_team_members_list_scoped_to_org(studio_admin_client, studio_org, other_user):
    UserFactory(org=studio_org, role=User.Role.MEMBER, email="teammate@example.com")

    res = studio_admin_client.get("/api/auth/team/members/")

    assert res.status_code == 200, res.content
    body = res.json()
    emails = {m["email"] for m in body["members"]}
    assert "teammate@example.com" in emails
    assert other_user.email not in emails
    assert body["seat_limit"] == 5
    assert body["seats_used"] == 2


def test_admin_can_remove_member_but_not_self(studio_admin_client, studio_org):
    member = UserFactory(org=studio_org, role=User.Role.MEMBER)

    res_self = studio_admin_client.delete(f"/api/auth/team/members/{studio_admin_client.user.id}/")
    assert res_self.status_code == 400

    res = studio_admin_client.delete(f"/api/auth/team/members/{member.id}/")
    assert res.status_code == 204
    assert not User.objects.filter(pk=member.pk).exists()


def test_admin_cannot_remove_member_of_other_org(studio_admin_client, other_user):
    res = studio_admin_client.delete(f"/api/auth/team/members/{other_user.id}/")

    assert res.status_code == 404
    assert User.objects.filter(pk=other_user.pk).exists()
