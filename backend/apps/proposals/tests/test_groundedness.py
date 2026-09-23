"""Pure unit tests for sentence-level groundedness scoring — no DB, no network."""

from types import SimpleNamespace
from unittest.mock import patch

from apps.proposals.groundedness import GROUNDED_THRESHOLD, score_groundedness

# 3-dim toy vectors keep cosine math easy to reason about by hand.
CHUNK_VECTOR = [1.0, 0.0, 0.0]
GROUNDED_SENTENCE_VECTOR = [1.0, 0.0, 0.0]  # identical -> cosine 1.0
UNGROUNDED_SENTENCE_VECTOR = [0.0, 1.0, 0.0]  # orthogonal -> cosine 0.0


def _chunk(vector=CHUNK_VECTOR):
    return SimpleNamespace(embedding=vector)


def test_no_chunks_returns_empty_result():
    result = score_groundedness({"executive_summary": "We deliver excellent results."}, [])
    assert result["overall_rate"] == 0.0
    assert result["sentence_total"] == 0


def test_no_sentences_returns_empty_result():
    result = score_groundedness({"pricing": ""}, [_chunk()])
    assert result["sentence_total"] == 0


def test_grounded_and_ungrounded_sentences_scored_separately():
    sections = {
        "executive_summary": (
            "We have delivered similar projects before. "  # grounded
            "Our CEO once climbed Mount Everest twice."  # ungrounded
        )
    }

    def fake_embed(texts, task_type="retrieval_document"):
        assert task_type == "retrieval_query"
        return [GROUNDED_SENTENCE_VECTOR, UNGROUNDED_SENTENCE_VECTOR]

    with patch("apps.proposals.groundedness.embed_texts", side_effect=fake_embed):
        result = score_groundedness(sections, [_chunk()])

    assert result["sentence_total"] == 2
    assert result["sentence_grounded"] == 1
    assert result["overall_rate"] == 0.5
    assert result["sections"]["executive_summary"]["grounded"] == 1
    assert result["sections"]["executive_summary"]["total"] == 2
    assert result["threshold"] == GROUNDED_THRESHOLD


def test_short_fragments_are_skipped():
    sections = {"why_us": "Thanks. We deliver excellent results for every client we work with."}

    def fake_embed(texts, task_type="retrieval_document"):
        assert texts == ["We deliver excellent results for every client we work with."]
        return [GROUNDED_SENTENCE_VECTOR]

    with patch("apps.proposals.groundedness.embed_texts", side_effect=fake_embed):
        result = score_groundedness(sections, [_chunk()])

    assert result["sentence_total"] == 1
