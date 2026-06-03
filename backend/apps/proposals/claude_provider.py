"""Anthropic Claude wrapper for proposal generation + RFP analysis + intent classification.

Uses Anthropic SDK with prompt caching enabled where it pays off (large system prompts
and RFP brief shared across the 3 calls per proposal).
"""

import json
import logging
import re
from functools import lru_cache

from anthropic import Anthropic, APIStatusError
from django.conf import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client() -> Anthropic:
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not configured")
    return Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def is_rate_limit_error(exc: Exception) -> bool:
    if isinstance(exc, APIStatusError):
        return exc.status_code in (429, 529)
    msg = str(exc).lower()
    return "429" in msg or "rate" in msg or "overloaded" in msg


def _extract_text(response) -> str:
    parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def _parse_json(raw: str, label: str) -> dict:
    # Strip common wrappers
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)

    # If we prefilled "{" the response starts with the rest of the object
    if not text.lstrip().startswith("{"):
        text = "{" + text

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Greedy match for outermost {...}
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise ValueError(f"{label} did not return valid JSON. Raw: {raw[:500]}") from None


JSON_PREFILL = [{"type": "text", "text": "{"}]


def generate_proposal(system_prompt: str, user_message: str, max_tokens: int = 10000) -> dict:
    """Pass 2: write the N-section proposal JSON. Uses assistant prefill to force JSON."""
    response = _client().messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": system_prompt
                + "\n\nCRITICAL: Respond with a single JSON object. No prose, no markdown fences, no preamble.",
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": JSON_PREFILL},
        ],
    )
    if response.stop_reason == "max_tokens":
        logger.error("Claude generation truncated at max_tokens=%s — output too long", max_tokens)
    return _parse_json(_extract_text(response), "Claude")


def analyze_rfp(prompt: str, rfp_text: str) -> dict:
    """Pass 1: structured RFP brief."""
    response = _client().messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=1500,
        system="Respond with a single JSON object. No prose, no markdown fences, no preamble.",
        messages=[
            {"role": "user", "content": f"{prompt}\n\nRFP TEXT:\n\n{rfp_text}"},
            {"role": "assistant", "content": JSON_PREFILL},
        ],
    )
    try:
        return _parse_json(_extract_text(response), "Claude RFP analyzer")
    except Exception as exc:
        logger.warning("Claude RFP analyzer parse failed: %s", exc)
        return {}


def classify_intent(prompt: str, snippet: str) -> dict:
    """Cheap intent classifier."""
    response = _client().messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=400,
        system="Respond with a single JSON object. No prose, no markdown fences, no preamble.",
        messages=[
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n\n{snippet}"},
            {"role": "assistant", "content": JSON_PREFILL},
        ],
    )
    return _parse_json(_extract_text(response), "Claude intent classifier")


TITLE_SYSTEM = (
    "You are a proposal-naming assistant. "
    "Read the RFP or project brief excerpt and output ONLY a concise 3-to-7 word title in "
    "Title Case that captures the project's core purpose. "
    "Output the title text only — no punctuation at the end, no quotes, no explanation."
)


def generate_title(rfp_snippet: str) -> str:
    """Extract a 3-7 word proposal title from the first ~400 chars of an RFP.

    Returns a plain string (never raises — caller handles exceptions).
    """
    response = _client().messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=30,
        system=TITLE_SYSTEM,
        messages=[
            {"role": "user", "content": f"RFP EXCERPT:\n\n{rfp_snippet[:400]}\n\nTitle:"},
        ],
    )
    return _extract_text(response).strip().strip("\"'")
