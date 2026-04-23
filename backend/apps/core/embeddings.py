import google.generativeai as genai
from django.conf import settings

_configured = False


def _ensure_configured():
    global _configured
    if not _configured:
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        _configured = True


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed a list of strings. Returns list of 768-dim vectors."""
    _ensure_configured()
    result = genai.embed_content(
        model=settings.EMBEDDING_MODEL,
        content=texts,
        task_type="retrieval_document",
    )
    return result["embedding"]


def embed_text(text: str) -> list[float]:
    _ensure_configured()
    result = genai.embed_content(
        model=settings.EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_query",
    )
    return result["embedding"]
