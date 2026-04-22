import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def ingest_document(self, document_id: str):
    from .models import Document, Chunk
    from .pipeline import extract_text, chunk_text
    from apps.core.embeddings import embed_texts

    try:
        doc = Document.objects.get(id=document_id)
        doc.status = Document.Status.PROCESSING
        doc.save(update_fields=["status"])

        text = extract_text(doc.file.path, doc.file_type)

        chunks_data = list(chunk_text(text))
        if not chunks_data:
            raise ValueError("No text could be extracted from document.")

        texts = [c["content"] for c in chunks_data]

        # Embed in batches of 100
        all_embeddings = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i: i + batch_size]
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
        try:
            doc = Document.objects.get(id=document_id)
            doc.status = Document.Status.FAILED
            doc.error_message = str(exc)
            doc.save(update_fields=["status", "error_message"])
        except Document.DoesNotExist:
            pass
        raise self.retry(exc=exc, countdown=60)
