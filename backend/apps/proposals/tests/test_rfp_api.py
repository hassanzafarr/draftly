"""RFP creation API tests: validation guards, file extraction, title derivation."""

from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.proposals.models import RFP

from .factories import VALID_RFP_TEXT

pytestmark = pytest.mark.django_db


def test_create_rfp_with_text(auth_client):
    res = auth_client.post(
        "/api/rfps/", {"title": "Scheduling Platform", "raw_text": VALID_RFP_TEXT}, format="json"
    )
    assert res.status_code == 201
    rfp = RFP.objects.get(id=res.data["id"])
    assert rfp.org == auth_client.user.org
    assert rfp.raw_text == VALID_RFP_TEXT


def test_rejects_missing_text_and_file(auth_client):
    res = auth_client.post("/api/rfps/", {"title": "Empty"}, format="json")
    assert res.status_code == 400


def test_rejects_too_short_text(auth_client):
    res = auth_client.post(
        "/api/rfps/", {"title": "Short", "raw_text": "build me an app"}, format="json"
    )
    assert res.status_code == 400
    assert "too short" in str(res.data).lower()


def test_rejects_text_over_max_chars(auth_client, settings):
    settings.RFP_MAX_CHARS = 1000
    res = auth_client.post(
        "/api/rfps/", {"title": "Huge", "raw_text": VALID_RFP_TEXT * 20}, format="json"
    )
    assert res.status_code == 400
    assert "too large" in str(res.data).lower()


def test_create_rfp_from_txt_file(auth_client):
    file = SimpleUploadedFile("brief.txt", VALID_RFP_TEXT.encode(), content_type="text/plain")
    res = auth_client.post("/api/rfps/", {"title": "From File", "file": file}, format="multipart")
    assert res.status_code == 201
    rfp = RFP.objects.get(id=res.data["id"])
    assert "patient scheduling platform" in rfp.raw_text


def test_rejects_unsupported_rfp_file_type(auth_client):
    file = SimpleUploadedFile("brief.csv", b"a,b,c", content_type="text/csv")
    res = auth_client.post("/api/rfps/", {"title": "Bad ext", "file": file}, format="multipart")
    assert res.status_code == 400


def test_blank_title_falls_back_to_heuristic(auth_client):
    """With LLM titling unavailable, the regex heuristics must still produce a title."""
    text = f"Project Name: Clinic Scheduling Revamp\n\n{VALID_RFP_TEXT}"
    with patch("apps.proposals.serializers._llm_title", return_value=""):
        res = auth_client.post("/api/rfps/", {"raw_text": text}, format="json")
    assert res.status_code == 201
    assert res.data["title"] == "Clinic Scheduling Revamp"


def test_rfps_are_org_scoped(auth_client, other_auth_client):
    res = auth_client.post(
        "/api/rfps/", {"title": "Mine", "raw_text": VALID_RFP_TEXT}, format="json"
    )
    rfp_id = res.data["id"]

    assert other_auth_client.get("/api/rfps/").data == []
    assert other_auth_client.get(f"/api/rfps/{rfp_id}/").status_code == 404
