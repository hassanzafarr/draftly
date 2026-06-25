"""SSE status-stream tests for proposals and documents.

SSE_MAX_DURATION_SECONDS is set to 0 so streams that would otherwise wait on
in-flight work emit their current state and immediately time out — no sleeping
in tests.
"""

import json

import pytest

from apps.documents.models import Document
from apps.documents.tests.factories import DocumentFactory
from apps.proposals.models import Proposal

from .factories import ProposalFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _fast_sse(settings):
    settings.SSE_MAX_DURATION_SECONDS = 0
    settings.SSE_POLL_INTERVAL_SECONDS = 0.001


def _events(response):
    """Parse a streamed SSE body into [(event, data), ...]."""
    body = b"".join(response.streaming_content).decode()
    parsed = []
    for frame in body.split("\n\n"):
        event, data = "message", None
        for line in frame.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        if data is not None:
            parsed.append((event, data))
    return parsed


# ---------------------------------------------------------------------------
# Proposal stream
# ---------------------------------------------------------------------------


def test_proposal_stream_emits_status_then_done_for_terminal_proposal(auth_client):
    proposal = ProposalFactory(rfp__org=auth_client.user.org, status=Proposal.Status.DRAFT)

    res = auth_client.get(f"/api/proposals/{proposal.id}/events/")
    assert res.status_code == 200
    assert res["Content-Type"] == "text/event-stream"

    events = _events(res)
    assert events[0][0] == "status"
    assert events[0][1]["status"] == "draft"
    assert events[-1][0] == "done"


def test_proposal_stream_times_out_while_generating(auth_client):
    proposal = ProposalFactory(
        rfp__org=auth_client.user.org,
        status=Proposal.Status.GENERATING,
        status_stage="drafting",
    )

    events = _events(auth_client.get(f"/api/proposals/{proposal.id}/events/"))
    assert events[0][0] == "status"
    assert events[0][1]["status_stage"] == "drafting"
    assert events[-1][0] == "timeout"


def test_proposal_stream_is_org_scoped(auth_client, other_auth_client):
    proposal = ProposalFactory(rfp__org=auth_client.user.org)

    res = other_auth_client.get(f"/api/proposals/{proposal.id}/events/")
    assert res.status_code == 404


def test_proposal_stream_requires_auth(api_client):
    proposal = ProposalFactory()
    res = api_client.get(f"/api/proposals/{proposal.id}/events/")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Document stream
# ---------------------------------------------------------------------------


def test_document_stream_done_when_nothing_in_flight(auth_client):
    DocumentFactory(org=auth_client.user.org, status=Document.Status.PROCESSED)

    events = _events(auth_client.get("/api/documents/events/"))
    assert events[0][0] == "status"
    assert events[0][1]["documents"][0]["status"] == "processed"
    assert events[-1][0] == "done"


def test_document_stream_times_out_while_processing(auth_client):
    DocumentFactory(org=auth_client.user.org, status=Document.Status.PROCESSING)

    events = _events(auth_client.get("/api/documents/events/"))
    assert events[0][0] == "status"
    assert events[-1][0] == "timeout"


def test_document_stream_excludes_other_orgs_docs(auth_client, other_org):
    DocumentFactory(org=other_org, status=Document.Status.PROCESSING)

    events = _events(auth_client.get("/api/documents/events/"))
    assert events[0][1]["documents"] == []
    assert events[-1][0] == "done"
