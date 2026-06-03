"""Post-generation quality signals for GenerationEvent telemetry."""

import re


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower())


def _proposal_text(sections: dict) -> str:
    return _normalize(" ".join(str(v) for v in sections.values() if v))


def _keyword_hits(haystack: str, needle: str) -> bool:
    """Loose match: every alphanumeric token >=3 chars in needle must appear in haystack."""
    tokens = [t for t in _normalize(needle).split() if len(t) >= 3]
    if not tokens:
        return False
    return all(t in haystack for t in tokens)


def evaluate_proposal(sections: dict, rfp_brief: dict) -> dict:
    """
    Compute coverage metrics for a generated proposal.
    Returns dict shaped to merge into GenerationEvent fields.
    """
    text = _proposal_text(sections or {})

    requirements = rfp_brief.get("key_requirements", []) or []
    red_flags = rfp_brief.get("red_flags", []) or []

    requirements_hit = sum(1 for r in requirements if _keyword_hits(text, r))
    red_flags_hit = sum(1 for r in red_flags if _keyword_hits(text, r))

    section_word_counts = {
        key: len(str(value or "").split()) for key, value in (sections or {}).items()
    }

    return {
        "requirements_total": len(requirements),
        "requirements_hit": requirements_hit,
        "red_flags_total": len(red_flags),
        "red_flags_hit": red_flags_hit,
        "section_word_counts": section_word_counts,
    }
