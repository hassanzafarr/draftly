"""Template API tests: built-in visibility, org isolation, CRUD rules."""

import pytest

from apps.proposals.builtin_templates import BUILTIN_TEMPLATES, seed_builtin_templates
from apps.proposals.models import Template

pytestmark = pytest.mark.django_db

BUILTIN_COUNT = len(BUILTIN_TEMPLATES)


@pytest.fixture(autouse=True)
def _builtin_templates(db):
    """Tests run with --no-migrations, so seed the builtins the migration would create."""
    seed_builtin_templates(Template)


def _create_payload(**overrides):
    payload = {
        "title": "Custom SEO Audit",
        "snippet": "Org-specific SEO proposal.",
        "category": "web",
        "accent": "cyan",
        "sections": ["Executive Summary", "Audit Findings", "Roadmap", "Pricing"],
    }
    payload.update(overrides)
    return payload


def test_list_returns_builtin_templates(auth_client):
    res = auth_client.get("/api/templates/")

    assert res.status_code == 200, res.content
    body = res.json()
    assert len(body) == BUILTIN_COUNT
    assert all(t["is_builtin"] for t in body)
    titles = {t["title"] for t in body}
    assert "Web Platform Redesign" in titles
    web = next(t for t in body if t["title"] == "Web Platform Redesign")
    assert web["sections_count"] == 10
    assert web["sections"][0] == "Executive Summary"


def test_create_org_template_and_org_isolation(auth_client, other_auth_client):
    res = auth_client.post("/api/templates/", _create_payload(), format="json")

    assert res.status_code == 201, res.content
    body = res.json()
    assert body["is_builtin"] is False
    assert body["sections_count"] == 4

    own = auth_client.get("/api/templates/").json()
    other = other_auth_client.get("/api/templates/").json()
    assert len(own) == BUILTIN_COUNT + 1
    assert len(other) == BUILTIN_COUNT
    assert "Custom SEO Audit" not in {t["title"] for t in other}


def test_create_requires_sections(auth_client):
    res = auth_client.post("/api/templates/", _create_payload(sections=[]), format="json")
    assert res.status_code == 400


def test_builtin_templates_are_immutable(auth_client):
    builtin = Template.objects.filter(org__isnull=True).first()

    patch = auth_client.patch(f"/api/templates/{builtin.id}/", {"title": "Hacked"}, format="json")
    delete = auth_client.delete(f"/api/templates/{builtin.id}/")

    assert patch.status_code == 403
    assert delete.status_code == 403
    builtin.refresh_from_db()
    assert builtin.title != "Hacked"


def test_update_and_delete_own_template(auth_client):
    created = auth_client.post("/api/templates/", _create_payload(), format="json").json()

    patch = auth_client.patch(
        f"/api/templates/{created['id']}/",
        {"title": "Renamed Audit", "sections": ["Summary", "Plan"]},
        format="json",
    )
    assert patch.status_code == 200, patch.content
    assert patch.json()["title"] == "Renamed Audit"
    assert patch.json()["sections_count"] == 2

    delete = auth_client.delete(f"/api/templates/{created['id']}/")
    assert delete.status_code == 204
    assert not Template.objects.filter(pk=created["id"]).exists()


def test_cannot_touch_other_orgs_template(auth_client, other_auth_client):
    created = auth_client.post("/api/templates/", _create_payload(), format="json").json()

    res_get = other_auth_client.get(f"/api/templates/{created['id']}/")
    res_del = other_auth_client.delete(f"/api/templates/{created['id']}/")

    assert res_get.status_code == 404
    assert res_del.status_code == 404
    assert Template.objects.filter(pk=created["id"]).exists()


def test_templates_require_auth(api_client):
    res = api_client.get("/api/templates/")
    assert res.status_code == 401
