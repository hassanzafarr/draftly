import json
import logging
import time
from urllib import error, request

from django.conf import settings

logger = logging.getLogger(__name__)

COHERE_RERANK_URL = "https://api.cohere.com/v2/rerank"


def rerank_chunks(query: str, chunks: list, top_k: int | None = None) -> tuple[list, dict]:
    """
    Rerank chunks against query using Cohere Rerank API.
    Returns (ordered_chunks, meta) where meta carries telemetry:
      {
        "used": bool,           # whether Cohere actually ran
        "latency_ms": int,      # rerank call wall time
        "scores": {chunk_id: float},  # rerank scores by chunk id (only if used)
        "error": str | None,
      }
    On any failure (no key, rate limit, network), returns first top_k of input unchanged.
    """
    keep = top_k or settings.RERANK_KEEP_TOP_K
    meta = {"used": False, "latency_ms": 0, "scores": {}, "error": None}

    if not settings.RERANK_ENABLED or not settings.COHERE_API_KEY:
        meta["error"] = "disabled_or_no_key"
        return list(chunks)[:keep], meta

    if not chunks:
        return [], meta

    documents = [c.content for c in chunks]

    payload = {
        "model": settings.COHERE_RERANK_MODEL,
        "query": query,
        "documents": documents,
        "top_n": min(keep, len(documents)),
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        COHERE_RERANK_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {settings.COHERE_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "draftly-backend/1.0 (+https://draftly.software)",
        },
        method="POST",
    )

    started = time.perf_counter()
    try:
        with request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        logger.warning(
            "Cohere rerank HTTP %s: %s — falling back to vector order", exc.code, details
        )
        meta["error"] = f"http_{exc.code}"
        meta["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return list(chunks)[:keep], meta
    except Exception as exc:
        logger.warning("Cohere rerank failed: %s — falling back to vector order", exc)
        meta["error"] = type(exc).__name__
        meta["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return list(chunks)[:keep], meta

    meta["latency_ms"] = int((time.perf_counter() - started) * 1000)
    results = data.get("results", [])
    if not results:
        meta["error"] = "empty_results"
        return list(chunks)[:keep], meta

    ordered = []
    for r in results:
        chunk = chunks[r["index"]]
        ordered.append(chunk)
        meta["scores"][str(chunk.id)] = r.get("relevance_score", 0.0)

    meta["used"] = True
    return ordered, meta
