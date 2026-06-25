"""Document upload + ingestion pipeline tests.

Celery runs eagerly in tests (CELERY_TASK_ALWAYS_EAGER), so POSTing a document
executes `ingest_document` inline. The only thing mocked is the embeddings API
(`apps.core.embeddings.embed_texts`) — extraction, chunking, and pgvector
inserts run for real against the test database.
"""

from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents.models import Chunk, Document

from .factories import DocumentFactory

pytestmark = pytest.mark.django_db

FAKE_VECTOR = [0.1] * 768

# Long enough to produce exactly one ~500-word chunk.
SAMPLE_TEXT = ("Draftly builds proposal automation software for agencies. " * 20).strip()


def _upload(client, *, name="profile.txt", content=None, category="company_profile"):
    file = SimpleUploadedFile(name, (content or SAMPLE_TEXT).encode(), content_type="text/plain")
    return client.post(
        "/api/documents/",
        {"file": file, "title": name, "category": category},
        format="multipart",
    )


def _mock_embed():
    return patch(
        "apps.core.embeddings.embed_texts",
        side_effect=lambda texts: [FAKE_VECTOR for _ in texts],
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_txt_upload_ingests_chunks_and_marks_processed(auth_client):
    with _mock_embed():
        res = _upload(auth_client)

    assert res.status_code == 201
    doc = Document.objects.get(id=res.data["id"])
    assert doc.status == Document.Status.PROCESSED
    assert doc.chunk_count > 0
    assert doc.chunk_count == Chunk.objects.filter(document=doc).count()

    chunk = Chunk.objects.filter(document=doc).first()
    assert chunk.org_id == auth_client.user.org_id
    assert chunk.metadata["source_title"] == "profile.txt"
    assert chunk.metadata["category"] == "company_profile"
    assert len(chunk.embedding) == 768


def test_upload_stores_selected_category(auth_client):
    with _mock_embed():
        res = _upload(auth_client, name="case.txt", category="case_studies")

    assert res.status_code == 201
    assert res.data["category"] == "case_studies"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_unsupported_extension_rejected(auth_client):
    res = _upload(auth_client, name="malware.exe")
    assert res.status_code == 400
    assert not Document.objects.exists()


def test_oversized_file_rejected(auth_client):
    res = _upload(auth_client, content="x" * (5 * 1024 * 1024 + 1))
    assert res.status_code == 400
    assert not Document.objects.exists()


# ---------------------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------------------


def test_embedding_rate_limit_marks_doc_failed_without_retry_loop(auth_client):
    """Rate-limit errors must surface as status=failed (skipping Celery retry)."""
    with patch(
        "apps.core.embeddings.embed_texts",
        side_effect=Exception("429 rate limit exceeded"),
    ):
        res = _upload(auth_client)

    assert res.status_code == 201
    doc = Document.objects.get(id=res.data["id"])
    assert doc.status == Document.Status.FAILED
    assert "429" in doc.error_message
    assert doc.chunks.count() == 0


def test_empty_document_fails_and_lands_in_dlq_after_retries(auth_client):
    """Non-rate-limit errors retry (eagerly inline here), then record a DLQ row.

    Run the task directly: in eager mode the terminal re-raise would otherwise
    propagate through the upload view and abort the request mid-test.
    """
    from apps.core.models import DeadLetterTask
    from apps.documents.tasks import ingest_document

    doc = DocumentFactory(org=auth_client.user.org, status=Document.Status.PENDING)
    doc.file.save("empty.txt", ContentFile(b"   "), save=True)

    with _mock_embed(), pytest.raises(ValueError, match="No text"):
        ingest_document.apply(args=[str(doc.id)], throw=True)

    doc.refresh_from_db()
    assert doc.status == Document.Status.FAILED
    assert "No text" in doc.error_message
    assert DeadLetterTask.objects.filter(task_name__contains="ingest_document").exists()


# ---------------------------------------------------------------------------
# Quota
# ---------------------------------------------------------------------------


def test_doc_quota_blocks_upload_at_limit(auth_client):
    org = auth_client.user.org
    DocumentFactory.create_batch(org.doc_quota, org=org, status=Document.Status.PROCESSED)

    res = _upload(auth_client)
    assert res.status_code == 403
    assert "quota" in res.data["detail"].lower()


def test_failed_docs_do_not_count_toward_quota(auth_client):
    org = auth_client.user.org
    DocumentFactory.create_batch(org.doc_quota, org=org, status=Document.Status.FAILED)

    with _mock_embed():
        res = _upload(auth_client)
    assert res.status_code == 201


# ---------------------------------------------------------------------------
# Multi-tenant isolation
# ---------------------------------------------------------------------------


def test_documents_are_org_scoped(auth_client, other_auth_client):
    with _mock_embed():
        res = _upload(auth_client)
    doc_id = res.data["id"]

    listing = other_auth_client.get("/api/documents/")
    assert listing.data == []

    detail = other_auth_client.get(f"/api/documents/{doc_id}/")
    assert detail.status_code == 404

    delete = other_auth_client.delete(f"/api/documents/{doc_id}/")
    assert delete.status_code == 404
    assert Document.objects.filter(id=doc_id).exists()
