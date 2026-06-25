"""Proposal generation flow tests.

Celery runs eagerly, so POST /rfps/{id}/generate/ executes
`generate_proposal_task` inline. The LLM pipeline
(`generate_proposal_with_metrics`) and the intent classifier are mocked; the
view logic, task state transitions, quota/length guards, and GenerationEvent
telemetry all run for real.
"""

from unittest.mock import patch

import pytest

from apps.proposals.models import GenerationEvent, Proposal

from .factories import ProposalFactory, RFPFactory

pytestmark = pytest.mark.django_db

SECTIONS = {key: f"{key} body" for key in Proposal.SECTION_KEYS}
METRICS = {
    "provider": "claude",
    "fetch_top_k": 20,
    "rerank_top_k": 6,
    "rerank_used": False,
    "rerank_latency_ms": 0,
    "retrieval_latency_ms": 12,
    "chunks_used": [],
    "generation_latency_ms": 800,
    "total_latency_ms": 900,
    "rfp_brief": {},
    "section_labels": {},
}


def _intent_ok():
    return patch(
        "apps.proposals.views.classify_rfp_intent",
        return_value={"is_rfp": True, "confidence": 1.0, "reason": "ok"},
    )


def _generator(return_value=(SECTIONS, METRICS), side_effect=None):
    return patch(
        "apps.proposals.generator.generate_proposal_with_metrics",
        return_value=return_value,
        side_effect=side_effect,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_generate_produces_draft_with_telemetry(auth_client):
    rfp = RFPFactory(org=auth_client.user.org)

    with _intent_ok(), _generator():
        res = auth_client.post(f"/api/rfps/{rfp.id}/generate/", {"tone": "formal"}, format="json")

    assert res.status_code == 202
    proposal = Proposal.objects.get(id=res.data["id"])
    assert proposal.status == Proposal.Status.DRAFT
    assert proposal.status_stage == "done"
    assert proposal.tone == "formal"
    assert proposal.sections == SECTIONS

    event = GenerationEvent.objects.get(proposal=proposal)
    assert event.success is True
    assert event.provider == "claude"


def test_invalid_tone_and_length_fall_back_to_defaults(auth_client):
    rfp = RFPFactory(org=auth_client.user.org)

    with _intent_ok(), _generator():
        res = auth_client.post(
            f"/api/rfps/{rfp.id}/generate/",
            {"tone": "sarcastic", "length": "novel"},
            format="json",
        )

    assert res.status_code == 202
    proposal = Proposal.objects.get(id=res.data["id"])
    assert proposal.tone == Proposal.Tone.PROFESSIONAL
    assert proposal.length == Proposal.Length.STANDARD


# ---------------------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------------------


def test_llm_rate_limit_marks_proposal_failed(auth_client):
    """Rate-limit errors skip Celery retry and surface as status=failed."""
    rfp = RFPFactory(org=auth_client.user.org)

    with _intent_ok(), _generator(side_effect=Exception("429 quota exceeded")):
        res = auth_client.post(f"/api/rfps/{rfp.id}/generate/", {}, format="json")

    assert res.status_code == 202
    proposal = Proposal.objects.get(id=res.data["id"])
    assert proposal.status == Proposal.Status.FAILED
    assert proposal.status_stage == "failed"
    assert "429" in proposal.error_message

    event = GenerationEvent.objects.get(proposal=proposal)
    assert event.success is False


# ---------------------------------------------------------------------------
# Guards: intent, length, quota
# ---------------------------------------------------------------------------


def test_non_rfp_input_rejected_before_consuming_quota(auth_client):
    rfp = RFPFactory(org=auth_client.user.org, raw_text="hello hello " * 30)

    with patch(
        "apps.proposals.views.classify_rfp_intent",
        return_value={"is_rfp": False, "confidence": 0.95, "reason": "repetitive filler"},
    ):
        res = auth_client.post(f"/api/rfps/{rfp.id}/generate/", {}, format="json")

    assert res.status_code == 400
    assert "valid RFP" in res.data["detail"]
    assert not Proposal.objects.exists()


def test_oversized_rfp_rejected_at_generate_time(auth_client, settings):
    """Guards legacy RFPs created before RFP_MAX_CHARS (or after it was lowered)."""
    settings.RFP_MAX_CHARS = 500
    rfp = RFPFactory(org=auth_client.user.org, raw_text="word " * 200)

    with _intent_ok():
        res = auth_client.post(f"/api/rfps/{rfp.id}/generate/", {}, format="json")

    assert res.status_code == 400
    assert "too large" in res.data["detail"].lower()
    assert not Proposal.objects.exists()


def test_monthly_proposal_quota_blocks_generation(auth_client):
    org = auth_client.user.org
    rfp = RFPFactory(org=org)
    ProposalFactory.create_batch(org.proposal_quota, rfp=rfp, org=org)

    with _intent_ok(), _generator():
        res = auth_client.post(f"/api/rfps/{rfp.id}/generate/", {}, format="json")

    assert res.status_code == 403
    assert "quota" in res.data["detail"].lower()
    assert Proposal.objects.count() == org.proposal_quota  # nothing new created


# ---------------------------------------------------------------------------
# Multi-tenant isolation
# ---------------------------------------------------------------------------


def test_cannot_generate_from_other_orgs_rfp(auth_client, other_auth_client):
    rfp = RFPFactory(org=auth_client.user.org)

    res = other_auth_client.post(f"/api/rfps/{rfp.id}/generate/", {}, format="json")
    assert res.status_code == 404


def test_proposals_are_org_scoped(auth_client, other_auth_client):
    proposal = ProposalFactory(rfp__org=auth_client.user.org)

    assert other_auth_client.get("/api/proposals/").data == []
    assert other_auth_client.get(f"/api/proposals/{proposal.id}/").status_code == 404
    assert other_auth_client.delete(f"/api/proposals/{proposal.id}/").status_code == 404
    assert Proposal.objects.filter(id=proposal.id).exists()
