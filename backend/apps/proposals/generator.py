import json
import re
import time
from urllib import error, request

import google.generativeai as genai
from django.conf import settings
from pgvector.django import CosineDistance

from apps.core.embeddings import embed_text
from apps.documents.models import Chunk

from . import claude_provider
from .reranker import rerank_chunks

DEFAULT_SECTIONS: list[tuple[str, str]] = [
    ("executive_summary", "Executive Summary"),
    ("understanding_requirements", "Understanding of Requirements"),
    ("proposed_solution", "Proposed Solution / Technical Approach"),
    ("relevant_experience", "Relevant Experience & Case Studies"),
    ("team_qualifications", "Team & Qualifications"),
    ("project_timeline", "Project Timeline"),
    ("methodology", "Methodology"),
    ("pricing", "Pricing / Commercial Proposal"),
    ("why_us", "Why Us"),
    ("appendix", "Appendix / Supporting Materials"),
]


def slugify_section(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return slug or "section"


def resolve_section_schema(custom_labels: list[str] | None) -> list[tuple[str, str]]:
    """Returns ordered list of (key, label). Empty/None custom_labels = default 10."""
    if not custom_labels:
        return list(DEFAULT_SECTIONS)
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for raw in custom_labels:
        label = (raw or "").strip()
        if not label:
            continue
        base = slugify_section(label)
        key = base
        i = 2
        while key in seen:
            key = f"{base}_{i}"
            i += 1
        seen.add(key)
        out.append((key, label))
    return out or list(DEFAULT_SECTIONS)


# Length presets — per-section word target, total cap, and LLM max_tokens budget.
LENGTH_PRESETS: dict[str, dict] = {
    "concise": {
        "per_section": "80-120 words (1 tight paragraph)",
        "total_cap": 1500,
        "max_tokens": 4000,
        "label": "concise",
    },
    "standard": {
        "per_section": "150-250 words (2 paragraphs)",
        "total_cap": 3000,
        "max_tokens": 8000,
        "label": "standard",
    },
    "detailed": {
        "per_section": "300-450 words (2-3 paragraphs)",
        "total_cap": 5000,
        "max_tokens": 14000,
        "label": "detailed",
    },
    "comprehensive": {
        "per_section": "500-700 words (3-4 paragraphs, deep specifics)",
        "total_cap": 8000,
        "max_tokens": 20000,
        "label": "comprehensive",
    },
}


def length_preset(length: str | None) -> dict:
    return LENGTH_PRESETS.get((length or "").lower(), LENGTH_PRESETS["standard"])


def build_section_instructions(schema: list[tuple[str, str]], length: str = "standard") -> str:
    keys = [k for k, _ in schema]
    schema_block = ",\n  ".join(f'"{k}": "<plain text string>"' for k in keys)
    keys_quoted = ", ".join(f'"{k}"' for k in keys)
    label_map = ", ".join(f'"{k}" → "{lbl}"' for k, lbl in schema)
    n = len(keys)
    preset = length_preset(length)
    return f"""
Generate a professional {n}-section proposal in JSON format.

OUTPUT SCHEMA (STRICT — do NOT deviate):
{{
  {schema_block}
}}

SECTION LABELS (use these as the meaning/topic for each key):
{label_map}

HARD RULES:
- The JSON object MUST have EXACTLY these {n} keys: {keys_quoted}. No more, no fewer. No renames. No extras.
- Every value MUST be a single plain-text string. NOT a nested object. NOT an array. NOT a list.
- Use \\n\\n inside the string to separate paragraphs within a section.
- No markdown headings (#), no bullet lists, no nested keys — just paragraph text.
- Treat the NEW RFP / PROJECT BRIEF as the primary source of truth.
- Use context chunks only as supporting company proof, case studies, or reusable capability language.
- Each context chunk is labeled by source type: "Company Profile" (brand, team, capabilities), "Past Proposal" (prior winning language, pricing, methodology), "Case Study" (concrete client outcomes). Weight chunks by source type when writing each section; do not pull pricing from Company Profile or team bios from Case Studies.
- Mirror the buyer's industry, terminology, compliance needs, must-have features, and explicit instructions.
- If the RFP is healthcare, mental health, finance, legal, or another regulated field, include the relevant compliance and safety requirements throughout the proposal.
- Do not replace the buyer's domain with a generic business domain.
- LENGTH MODE: {preset['label']}. Each section should be {preset['per_section']}. Keep total proposal under {preset['total_cap']} words. Calibrate detail and specificity to this length — concise drops to one focused paragraph; comprehensive adds concrete examples, metrics, and implementation depth.
- Use professional business language.
- Return valid JSON only — no markdown fences, no extra text outside the JSON object.
"""


_configured = False


def _ensure_configured():
    global _configured
    if not _configured:
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        _configured = True


def generate_title_with_gemini(rfp_snippet: str) -> str:
    """Extract a 3-7 word proposal title using Gemini Flash.

    Returns a plain string (never raises — caller handles exceptions).
    """
    _ensure_configured()
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=(
            "You are a proposal-naming assistant. "
            "Read the RFP or project brief excerpt and output ONLY a concise 3-to-7 word title in "
            "Title Case that captures the project's core purpose. "
            "Output the title text only — no punctuation at the end, no quotes, no explanation."
        ),
        generation_config={"max_output_tokens": 30},
    )
    response = model.generate_content(f"RFP EXCERPT:\n\n{rfp_snippet[:400]}\n\nTitle:")
    return (response.text or "").strip().strip("\"'")


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "429" in message or "quota" in message or "rate" in message


SECTION_SCHEMA = [k for k, _ in DEFAULT_SECTIONS]


def _flatten_value(value) -> str:
    """Coerce any structure into plain text. Recursively walks dicts/lists."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, int | float | bool):
        return str(value)
    if isinstance(value, list):
        return "\n\n".join(_flatten_value(v) for v in value if v)
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            flat = _flatten_value(v)
            if not flat:
                continue
            if isinstance(v, dict | list):
                # Use the key as a label paragraph
                label = str(k).replace("_", " ").title()
                parts.append(f"{label}: {flat}")
            else:
                parts.append(flat)
        return "\n\n".join(parts)
    return str(value)


def _normalize_sections(raw_sections: dict, schema_keys: list[str] | None = None) -> dict:
    """Coerce LLM output to the requested schema. Preserves key order."""
    keys = schema_keys if schema_keys is not None else SECTION_SCHEMA
    out: dict[str, str] = {}
    for key in keys:
        out[key] = _flatten_value(raw_sections.get(key, ""))

    # Catch keys the LLM invented. If "appendix" is part of the schema, dump them there;
    # otherwise append into the last section so nothing is lost.
    extras = []
    for k, v in raw_sections.items():
        if k not in keys:
            label = str(k).replace("_", " ").title()
            flat = _flatten_value(v)
            if flat:
                extras.append(f"{label}\n\n{flat}")
    if extras:
        bucket = "appendix" if "appendix" in out else keys[-1]
        existing = out.get(bucket, "")
        out[bucket] = "\n\n".join([existing] + extras).strip()

    return out


def _recover_truncated_json(text: str) -> dict | None:
    """Best-effort recovery for JSON truncated mid-value (token limit hit).

    Finds the last complete key-value pair, closes the object, and parses
    whatever sections were fully written before the cut-off.
    """
    import logging

    log = logging.getLogger(__name__)

    # Find last position where a complete string value ends: ..."<value>"\s*(,|\n)
    # Walk backwards looking for the last complete "key": "value" boundary.
    last_complete = re.search(r'("(?:[^"\\]|\\.)*")\s*(?:,\s*"|\s*\})', text[::-1])
    if not last_complete:
        return None

    # Trim to just past the last confirmed complete value, then close the object.
    cut = len(text) - last_complete.start()
    # Strip trailing comma/whitespace and close
    candidate = text[:cut].rstrip().rstrip(",").rstrip() + "\n}"
    try:
        parsed = json.loads(candidate)
        log.warning("Recovered truncated JSON: parsed %d keys from partial response", len(parsed))
        return parsed
    except json.JSONDecodeError:
        return None


def _parse_sections(raw: str, provider: str, schema_keys: list[str] | None = None) -> dict:
    import logging

    log = logging.getLogger(__name__)

    # Strip markdown code fences Gemini occasionally adds despite response_mime_type=json
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try regex extraction (handles leading/trailing non-JSON text)
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                parsed = None
        else:
            parsed = None

        # Regex found nothing (no closing }) — likely token truncation mid-JSON
        if parsed is None and cleaned.lstrip().startswith("{"):
            log.warning("%s response appears truncated (no closing }). Attempting recovery.", provider)
            parsed = _recover_truncated_json(cleaned)

        if parsed is None:
            raise ValueError(
                f"{provider} did not return valid JSON. Raw: {raw[:300]!r}"
            ) from None

    return _normalize_sections(parsed, schema_keys)


CATEGORY_LABELS = {
    "company_profile": "Company Profile",
    "past_proposals": "Past Proposal",
    "case_studies": "Case Study",
}


def _format_context(chunks: list) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.metadata.get("source_title", "Unknown")
        category = CATEGORY_LABELS.get(chunk.metadata.get("category"), "Reference")
        parts.append(f"[Source {i} | {category}: {source}]\n{chunk.content}")
    return "\n\n---\n\n".join(parts)


def retrieve_chunks_with_metrics(
    org_id: str, query_text: str, top_k: int | None = None
) -> tuple[list, dict]:
    """Fetch via vector search, rerank, return chunks + telemetry."""
    fetch_k = top_k or settings.RERANK_FETCH_TOP_K

    started = time.perf_counter()
    query_vector = embed_text(query_text)
    vector_chunks = list(
        Chunk.objects.filter(org_id=org_id)
        .annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance")[:fetch_k]
    )
    vector_rank_by_id = {str(c.id): i for i, c in enumerate(vector_chunks)}

    reranked, rerank_meta = rerank_chunks(query_text, vector_chunks)
    retrieval_latency_ms = int((time.perf_counter() - started) * 1000)

    chunks_used = []
    for chunk in reranked:
        cid = str(chunk.id)
        chunks_used.append(
            {
                "chunk_id": cid,
                "document_id": chunk.metadata.get("document_id"),
                "source_title": chunk.metadata.get("source_title", "Unknown"),
                "category": chunk.metadata.get("category"),
                "vector_rank": vector_rank_by_id.get(cid),
                "rerank_score": rerank_meta["scores"].get(cid),
            }
        )

    meta = {
        "fetch_top_k": fetch_k,
        "rerank_top_k": len(reranked),
        "rerank_used": rerank_meta["used"],
        "rerank_latency_ms": rerank_meta["latency_ms"],
        "rerank_error": rerank_meta["error"],
        "retrieval_latency_ms": retrieval_latency_ms,
        "chunks_used": chunks_used,
    }
    return reranked, meta


def retrieve_context(org_id: str, query_text: str, top_k: int | None = None) -> str:
    """Backward-compatible wrapper returning only the context string."""
    chunks, _ = retrieve_chunks_with_metrics(org_id, query_text, top_k)
    return _format_context(chunks)


RFP_ANALYSIS_PROMPT = """
Analyze the RFP/project brief below and return a JSON object with these exact keys:
- client_name: string — name of the client or organization issuing the RFP
- industry: string — specific industry/domain (e.g. "mental health services", "fintech", "government procurement")
- compliance_requirements: array of strings — regulations, standards, certifications required (e.g. "HIPAA", "SOC 2", "ISO 27001")
- key_requirements: array of strings — core deliverables and must-have features explicitly stated
- evaluation_criteria: array of strings — how the proposal will be scored/evaluated (extract from scoring rubric if present)
- budget_signals: string — any budget range, pricing expectations, or cost constraints mentioned (or "not specified")
- timeline: string — project timeline, deadlines, or phasing mentioned (or "not specified")
- emphasized_sections: array of strings — which of these proposal sections the RFP emphasizes most (from: executive_summary, understanding_requirements, proposed_solution, relevant_experience, team_qualifications, project_timeline, methodology, pricing, why_us, appendix)
- red_flags: array of strings — disqualifiers, exclusions, or strict requirements that must not be missed
- tone_preference: string — inferred preferred tone from RFP language (professional/formal/persuasive/technical/friendly)

Return valid JSON only. No markdown fences.
"""


def _analyze_rfp(rfp_text: str) -> dict:
    """Pass 1: extract structured understanding of the RFP before writing.

    Tries Claude first (primary), falls back to Gemini on failure.
    """
    if settings.CLAUDE_ENABLED and settings.ANTHROPIC_API_KEY:
        try:
            return claude_provider.analyze_rfp(RFP_ANALYSIS_PROMPT, rfp_text)
        except Exception as exc:
            logger_msg = f"Claude RFP analyzer failed, falling back to Gemini: {exc}"
            import logging

            logging.getLogger(__name__).warning(logger_msg)

    _ensure_configured()
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        generation_config={
            "max_output_tokens": 1024,
            "response_mime_type": "application/json",
        },
    )
    prompt = f"{RFP_ANALYSIS_PROMPT}\n\nRFP TEXT:\n\n{rfp_text}"
    response = model.generate_content(prompt)
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {}


TONE_INSTRUCTIONS = {
    "professional": "Write in a professional tone — balanced, credible, and polished with clear business language.",
    "formal": "Write in a formal tone — structured, precise, and authoritative with no colloquialisms.",
    "persuasive": "Write in a persuasive tone — confident and client-focused, emphasizing value, outcomes, and why we are the best choice.",
    "friendly": "Write in a friendly tone — warm, approachable, and conversational while remaining competent and helpful.",
    "technical": "Write in a technical tone — detailed and precise, using domain-specific terminology and emphasizing methodology, specs, and implementation depth.",
}


def _build_prompts(
    context: str,
    rfp_text: str,
    tone: str = "professional",
    rfp_brief: dict | None = None,
    schema: list[tuple[str, str]] | None = None,
    custom_schema: bool = False,
    length: str = "standard",
) -> tuple[str, str]:
    # Use tone from Pass 1 analysis if not overridden
    if rfp_brief and tone == "professional":
        tone = rfp_brief.get("tone_preference", "professional")
    tone_instruction = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["professional"])
    schema = schema or list(DEFAULT_SECTIONS)
    system_prompt = (
        "You are an expert proposal writer for a professional services firm. "
        "You write highly tailored, technically accurate proposals based strictly on provided context. "
        f"TONE INSTRUCTION: {tone_instruction} " + build_section_instructions(schema, length=length)
    )

    brief_block = ""
    if rfp_brief:
        lines = [
            "RFP ANALYSIS (use this to guide every section):",
            f"- Client: {rfp_brief.get('client_name', 'Unknown')}",
            f"- Industry/Domain: {rfp_brief.get('industry', 'Unknown')}",
            f"- Compliance Requirements: {', '.join(rfp_brief.get('compliance_requirements', [])) or 'None stated'}",
            f"- Key Requirements: {'; '.join(rfp_brief.get('key_requirements', []))}",
            f"- Evaluation Criteria: {'; '.join(rfp_brief.get('evaluation_criteria', []))}",
            f"- Budget Signals: {rfp_brief.get('budget_signals', 'Not specified')}",
            f"- Timeline: {rfp_brief.get('timeline', 'Not specified')}",
        ]
        # emphasized_sections only meaningful for default 10-section schema
        if not custom_schema:
            lines.append(
                f"- Emphasized Sections: {', '.join(rfp_brief.get('emphasized_sections', []))}"
            )
        lines.append(
            f"- Red Flags / Must-Nots: {'; '.join(rfp_brief.get('red_flags', [])) or 'None'}"
        )
        brief_block = "\n".join(lines) + "\n\n"

    user_message = (
        f"{brief_block}"
        f"CONTEXT FROM OUR HISTORICAL PROPOSALS AND CASE STUDIES:\n\n{context}\n\n"
        f"---\n\nNEW RFP / PROJECT BRIEF:\n\n{rfp_text}\n\n"
        "Generate the proposal JSON now."
    )
    return system_prompt, user_message


def _generate_with_gemini(
    system_prompt: str,
    user_message: str,
    schema_keys: list[str] | None = None,
    max_tokens: int = 8192,
) -> dict:
    import logging

    log = logging.getLogger(__name__)

    _ensure_configured()
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=system_prompt,
        generation_config={
            "max_output_tokens": max_tokens,
            "response_mime_type": "application/json",
        },
    )

    response = model.generate_content(user_message)
    candidate = (response.candidates or [None])[0]
    finish_reason = getattr(candidate, "finish_reason", "unknown") if candidate else "no_candidate"
    raw_len = len(response.text or "")
    approx_input_tokens = (len(system_prompt) + len(user_message)) // 4
    log.info(
        "Gemini response: finish_reason=%s raw_len=%d approx_input_tokens=%d max_output_tokens=%d",
        finish_reason,
        raw_len,
        approx_input_tokens,
        max_tokens,
    )
    if str(finish_reason) in ("2", "MAX_TOKENS", "FinishReason.MAX_TOKENS"):
        log.warning(
            "Gemini hit max_output_tokens (%d) — JSON likely truncated. raw_len=%d",
            max_tokens,
            raw_len,
        )
    return _parse_sections(response.text, "Gemini", schema_keys)


def _generate_with_groq(
    system_prompt: str,
    user_message: str,
    schema_keys: list[str] | None = None,
    max_tokens: int = 8192,
) -> dict:
    if not settings.GROQ_API_KEY:
        raise ValueError("Gemini hit a rate limit and GROQ_API_KEY is not configured.")

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "draftly-backend/1.0 (+https://draftly.software)",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(f"Groq request failed with HTTP {exc.code}: {details}") from exc

    raw = data["choices"][0]["message"]["content"]
    return _parse_sections(raw, "Groq", schema_keys)


def _generate_with_fallbacks(
    system_prompt: str,
    user_message: str,
    schema_keys: list[str] | None = None,
    max_tokens: int = 8192,
) -> tuple[str, dict]:
    """Try Claude (primary) → Gemini → Groq. Returns (provider_name, sections)."""
    import logging

    log = logging.getLogger(__name__)

    # Groq llama-3.1-8b free tier caps at 6k TPM — useless for our ~16k-token prompt.
    # Skip Groq entirely if prompt is bigger than the free-tier ceiling.
    approx_tokens = (len(system_prompt) + len(user_message)) // 4
    groq_usable = approx_tokens < 5500

    if settings.CLAUDE_ENABLED and settings.ANTHROPIC_API_KEY:
        try:
            sections = claude_provider.generate_proposal(
                system_prompt, user_message, max_tokens=max_tokens
            )
            return "claude", _normalize_sections(sections, schema_keys)
        except Exception as exc:
            log.warning("Claude generation failed, falling back to Gemini: %s", exc)

    try:
        sections = _generate_with_gemini(
            system_prompt, user_message, schema_keys, max_tokens=max_tokens
        )
        return "gemini", sections
    except Exception as exc:
        should_fallback = _is_rate_limit_error(exc) or isinstance(exc, ValueError)
        if should_fallback and groq_usable and settings.GROQ_API_KEY:
            log.warning("Gemini failed (%s), falling back to Groq: %s", type(exc).__name__, exc)
            sections = _generate_with_groq(
                system_prompt, user_message, schema_keys, max_tokens=max_tokens
            )
            return "groq", sections
        raise


def generate_proposal_sync(
    rfp_text: str, org_id: str, tone: str = "professional", length: str = "standard"
) -> dict:
    """Two-pass proposal generation: analyze RFP first, then write using structured brief."""
    sections, _ = generate_proposal_with_metrics(rfp_text, org_id, tone, length=length)
    return sections


def generate_proposal_with_metrics(
    rfp_text: str,
    org_id: str,
    tone: str = "professional",
    on_stage=None,
    custom_section_labels: list[str] | None = None,
    length: str = "standard",
) -> tuple[dict, dict]:
    """
    Two-pass generation + telemetry.
    Returns (sections_dict, metrics_dict).
    metrics_dict shape matches GenerationEvent fields plus rfp_brief.

    on_stage(stage: str, meta: dict) — optional callback fired at each phase
    so callers can persist progress for UI polling.
    """
    overall_started = time.perf_counter()

    def _emit(stage: str, meta: dict | None = None):
        if on_stage:
            try:
                on_stage(stage, meta or {})
            except Exception:
                pass

    _emit("analyzing", {})
    try:
        rfp_brief = _analyze_rfp(rfp_text)
    except Exception:
        rfp_brief = {}

    _emit(
        "retrieving",
        {
            "client": rfp_brief.get("client_name"),
            "industry": rfp_brief.get("industry"),
        },
    )
    chunks, retrieval_meta = retrieve_chunks_with_metrics(org_id, rfp_text)
    context = _format_context(chunks)
    schema = resolve_section_schema(custom_section_labels)
    is_custom = bool(custom_section_labels)
    schema_keys = [k for k, _ in schema]
    system_prompt, user_message = _build_prompts(
        context,
        rfp_text,
        tone,
        rfp_brief=rfp_brief,
        schema=schema,
        custom_schema=is_custom,
        length=length,
    )
    preset = length_preset(length)

    docs_seen: list[str] = []
    for c in retrieval_meta.get("chunks_used", []):
        title = c.get("source_title")
        if title and title not in docs_seen:
            docs_seen.append(title)
    top_chunk = (retrieval_meta.get("chunks_used") or [{}])[0]

    _emit(
        "drafting",
        {
            "chunks": retrieval_meta.get("rerank_top_k", 0),
            "fetched": retrieval_meta.get("fetch_top_k", 0),
            "docs": docs_seen[:5],
            "top_source": top_chunk.get("source_title"),
            "top_category": top_chunk.get("category"),
            "rerank_used": retrieval_meta.get("rerank_used", False),
        },
    )

    gen_started = time.perf_counter()
    provider, sections = _generate_with_fallbacks(
        system_prompt,
        user_message,
        schema_keys,
        max_tokens=preset["max_tokens"],
    )
    generation_latency_ms = int((time.perf_counter() - gen_started) * 1000)

    _emit("polishing", {"provider": provider, "sections": len(sections)})

    metrics = {
        **retrieval_meta,
        "provider": provider,
        "generation_latency_ms": generation_latency_ms,
        "total_latency_ms": int((time.perf_counter() - overall_started) * 1000),
        "rfp_brief": rfp_brief,
        "section_labels": {k: lbl for k, lbl in schema} if is_custom else {},
    }
    return sections, metrics
