import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def ingest_document(self, document_id: str):
    from django.core.files.base import ContentFile

    from apps.core.embeddings import embed_texts

    from .models import Chunk, Document
    from .pipeline import chunk_text, extract_text
    from .security import PDFSecurityError, validate_and_sanitize_pdf

    try:
        doc = Document.objects.get(id=document_id)
        doc.status = Document.Status.PROCESSING
        doc.save(update_fields=["status"])

        with doc.file.open("rb") as fh:
            data = fh.read()

        if doc.file_type == Document.FileType.PDF:
            try:
                sanitized = validate_and_sanitize_pdf(data)
            except PDFSecurityError as sec_exc:
                doc.status = Document.Status.FAILED
                doc.error_message = str(sec_exc)
                doc.save(update_fields=["status", "error_message"])
                logger.warning(
                    "Document %s rejected by security check: %s",
                    document_id,
                    sec_exc,
                )
                return
            if sanitized != data:
                file_name = doc.file.name
                doc.file.save(file_name, ContentFile(sanitized), save=False)
                doc.save(update_fields=["file"])
                data = sanitized

        text = extract_text(data, doc.file_type)

        chunks_data = list(chunk_text(text))
        if not chunks_data:
            raise ValueError("No text could be extracted from document.")

        texts = [c["content"] for c in chunks_data]

        # Embed in batches of 100
        all_embeddings = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            all_embeddings.extend(embed_texts(batch))

        # Delete existing chunks (re-ingest scenario)
        Chunk.objects.filter(document=doc).delete()

        chunks_to_create = [
            Chunk(
                document=doc,
                org=doc.org,
                content=chunks_data[i]["content"],
                embedding=all_embeddings[i],
                metadata={
                    "char_offset": chunks_data[i]["char_offset"],
                    "source_title": doc.title,
                    "document_id": str(doc.id),
                    "category": doc.category,
                },
            )
            for i in range(len(chunks_data))
        ]
        Chunk.objects.bulk_create(chunks_to_create, batch_size=200)

        doc.status = Document.Status.PROCESSED
        doc.chunk_count = len(chunks_to_create)
        doc.save(update_fields=["status", "chunk_count"])
        logger.info("Ingested document %s: %d chunks", document_id, len(chunks_to_create))

    except Exception as exc:
        logger.error("Failed to ingest document %s: %s", document_id, exc)
        org_id = ""
        try:
            doc = Document.objects.get(id=document_id)
            org_id = str(doc.org_id)
            doc.status = Document.Status.FAILED
            doc.error_message = str(exc)
            doc.save(update_fields=["status", "error_message"])
        except Document.DoesNotExist:
            pass
        if "429" in str(exc) or "quota" in str(exc).lower() or "rate" in str(exc).lower():
            return
        if self.request.retries >= self.max_retries:
            from apps.core.dlq import record_failure

            record_failure(
                task_name=self.name,
                task_id=self.request.id or "",
                args=(document_id,),
                exception=exc,
                org_id=org_id,
            )
            raise
        raise self.retry(exc=exc, countdown=60)
