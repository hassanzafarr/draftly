import json
import logging
import re

import google.generativeai as genai
from django.conf import settings

from . import claude_provider

logger = logging.getLogger(__name__)

INTENT_PROMPT = """You are a strict classifier. Decide whether the text below is a real RFP, project brief, scope-of-work, or proposal request that a vendor could realistically respond to with a proposal.

Return JSON only with these exact keys:
- is_rfp: boolean
- confidence: number between 0 and 1
- reason: short string explaining the decision (max 200 chars)

Set is_rfp=true ONLY if the text contains concrete project information such as: client/buyer context, scope/deliverables, requirements, evaluation criteria, timeline, budget, or domain-specific needs.

Set is_rfp=false (high confidence 0.9+) for any of these:
- Greetings, single words, or short phrases ("hello", "test", "hi there")
- Repeated/filler text ("lorem ipsum", "this is fake this is fake...", "asdf asdf...")
- Gibberish, random characters, or keyboard mashing
- Off-topic content unrelated to a project
- Text that is long but says nothing actionable
- Placeholder or sample text without real requirements

Be strict. When in doubt, reject.
"""

_configured = False


def _ensure_configured():
    global _configured
    if not _configured:
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        _configured = True


def classify_rfp_intent(text: str) -> dict:
    """Cheap LLM check. Returns {is_rfp, confidence, reason}.

    Fails open: on any error, returns is_rfp=True so outages don't block users.
    """
    if not getattr(settings, "RFP_INTENT_CHECK_ENABLED", True):
        return {"is_rfp": True, "confidence": 1.0, "reason": "intent check disabled"}

    snippet = (text or "").strip()[:4000]
    if not snippet:
        return {"is_rfp": False, "confidence": 1.0, "reason": "empty input"}

    # Cheap heuristics — catch obvious junk before burning LLM call
    words = snippet.lower().split()
    word_count = len(words)

    # Repetition check
    if word_count >= 20:
        unique_ratio = len(set(words)) / word_count
        if unique_ratio < 0.30:
            return {
                "is_rfp": False,
                "confidence": 0.95,
                "reason": f"text is repetitive (unique word ratio {unique_ratio:.2f}) — not a real RFP",
            }

    # Sliding-window phrase repetition (catches "X X X X" where X is multi-word)
    if word_count >= 30:
        for window in (3, 4, 5):
            phrases = [" ".join(words[i : i + window]) for i in range(word_count - window + 1)]
            if phrases:
                top_count = max(phrases.count(p) for p in set(phrases))
                if top_count / len(phrases) > 0.25:
                    return {
                        "is_rfp": False,
                        "confidence": 0.95,
                        "reason": "text contains repeated phrase — not a real RFP",
                    }

    # RFP keyword signal — real RFPs almost always mention at least one of these
    RFP_SIGNALS = {
        "rfp",
        "proposal",
        "project",
        "scope",
        "requirements",
        "deliverables",
        "timeline",
        "budget",
        "vendor",
        "client",
        "deadline",
        "specification",
        "services",
        "solution",
        "system",
        "platform",
        "implementation",
        "development",
        "design",
        "build",
        "deploy",
        "integrate",
        "feature",
        "milestone",
        "objective",
        "goal",
        "stakeholder",
        "team",
        "phase",
        "deliverable",
        "criteria",
        "evaluation",
    }
    signal_hits = len(set(words) & RFP_SIGNALS)
    if word_count >= 30 and signal_hits == 0:
        return {
            "is_rfp": False,
            "confidence": 0.9,
            "reason": "no project/RFP terminology detected — not a real brief",
        }

    try:
        data = None

        if settings.CLAUDE_ENABLED and settings.ANTHROPIC_API_KEY:
            try:
                data = claude_provider.classify_intent(INTENT_PROMPT, snippet)
            except Exception as exc:
                logger.warning("Claude intent classifier failed, falling back to Gemini: %s", exc)

        if data is None:
            _ensure_configured()
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                generation_config={
                    "max_output_tokens": 512,
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                },
                system_instruction=(
                    "Output ONLY a single JSON object. No preamble, no markdown, no explanation. "
                    "Start with { and end with }."
                ),
            )
            response = model.generate_content(f"{INTENT_PROMPT}\n\nTEXT:\n\n{snippet}")
            raw = response.text or ""
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if not match:
                    raise ValueError("classifier returned no JSON") from None
                data = json.loads(match.group())

        result = {
            "is_rfp": bool(data.get("is_rfp", True)),
            "confidence": float(data.get("confidence", 0.0)),
            "reason": str(data.get("reason", ""))[:300],
        }
        logger.info("RFP intent classifier: %s", result)
        return result
    except Exception as exc:
        logger.warning("RFP intent classifier failed: %s", exc)
        # Fail-closed if text has weak RFP signal; fail-open otherwise
        if word_count < 50 or signal_hits < 2:
            return {
                "is_rfp": False,
                "confidence": 0.7,
                "reason": "could not verify input as RFP and signal is weak",
            }
        return {"is_rfp": True, "confidence": 0.0, "reason": f"classifier error: {exc}"}
