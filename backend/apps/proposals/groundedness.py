"""Sentence-level groundedness check: does each generated sentence trace back
to a retrieved chunk, or is it unsupported / hallucinated?

Method: split generated section text into sentences, embed each sentence,
cosine-compare against the embeddings of the chunks actually fed to the LLM
for this proposal. A sentence is "grounded" if its best match clears
GROUNDED_THRESHOLD. This is a similarity proxy, not entailment — it catches
sentences with no supporting source in the retrieved context, which is the
common failure mode (invented client names, numbers, claims).
"""

import re

import numpy as np

from apps.core.embeddings import embed_texts

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
MIN_SENTENCE_WORDS = 4  # skip short fragments/headers — too noisy to score
GROUNDED_THRESHOLD = 0.72


def _split_sentences(text: str) -> list[str]:
    if not text:
        return []
    flat = text.replace("\n", " ").strip()
    if not flat:
        return []
    candidates = SENTENCE_SPLIT_RE.split(flat)
    return [s.strip() for s in candidates if len(s.split()) >= MIN_SENTENCE_WORDS]


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def score_groundedness(sections: dict, chunks: list) -> dict:
    """
    sections: {section_key: text} — the generated proposal
    chunks: Chunk model instances actually used as retrieval context (post-rerank)

    Returns: {
        "overall_rate": float,
        "sentence_total": int,
        "sentence_grounded": int,
        "threshold": float,
        "sections": {section_key: {"total": int, "grounded": int, "rate": float}},
    }
    Empty/zero result (not an exception) if there's nothing to score.
    """
    empty = {
        "overall_rate": 0.0,
        "sentence_total": 0,
        "sentence_grounded": 0,
        "threshold": GROUNDED_THRESHOLD,
        "sections": {},
    }

    chunk_vectors = [
        np.asarray(c.embedding, dtype=float) for c in (chunks or []) if c.embedding is not None
    ]
    if not chunk_vectors:
        return empty

    all_sentences: list[tuple[str, str]] = []
    for key, text in (sections or {}).items():
        for sentence in _split_sentences(str(text or "")):
            all_sentences.append((key, sentence))

    if not all_sentences:
        return empty

    sentence_vectors = embed_texts([s for _, s in all_sentences], task_type="retrieval_query")

    per_section: dict[str, dict] = {}
    grounded_total = 0
    for (key, _sentence), raw_vec in zip(all_sentences, sentence_vectors, strict=False):
        vec = np.asarray(raw_vec, dtype=float)
        best_score = max(_cosine(vec, cv) for cv in chunk_vectors)
        bucket = per_section.setdefault(key, {"total": 0, "grounded": 0})
        bucket["total"] += 1
        if best_score >= GROUNDED_THRESHOLD:
            bucket["grounded"] += 1
            grounded_total += 1

    for bucket in per_section.values():
        bucket["rate"] = round(bucket["grounded"] / bucket["total"], 3) if bucket["total"] else 0.0

    total = len(all_sentences)
    return {
        "overall_rate": round(grounded_total / total, 3) if total else 0.0,
        "sentence_total": total,
        "sentence_grounded": grounded_total,
        "threshold": GROUNDED_THRESHOLD,
        "sections": per_section,
    }
