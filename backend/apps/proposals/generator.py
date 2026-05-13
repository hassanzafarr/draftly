import json
import re
import time
from urllib import error, request
import google.generativeai as genai
from django.conf import settings
from pgvector.django import CosineDistance
from apps.documents.models import Chunk
from apps.core.embeddings import embed_text
from .reranker import rerank_chunks
from . import claude_provider

SECTION_INSTRUCTIONS = """
Generate a professional 10-section proposal in JSON format with these exact keys:
- executive_summary
- understanding_requirements
- proposed_solution
- relevant_experience
- team_qualifications
- project_timeline
- methodology
- pricing
- why_us
- appendix

Rules:
- Treat the NEW RFP / PROJECT BRIEF as the primary source of truth.
- Use context chunks only as supporting company proof, case studies, or reusable capability language.
- Each context chunk is labeled by source type: "Company Profile" (brand, team, capabilities — use for executive_summary, team_qualifications, why_us), "Past Proposal" (prior winning language, pricing, methodology — use for methodology, pricing, proposed_solution), "Case Study" (concrete client outcomes — use for relevant_experience, proposed_solution, why_us). Weight chunks by source type when writing each section; do not pull pricing from Company Profile or team bios from Case Studies.
- Mirror the buyer's industry, terminology, compliance needs, must-have features, and explicit instructions.
- If the RFP is healthcare, mental health, finance, legal, or another regulated field, include the relevant compliance and safety requirements throughout the proposal.
- Do not replace the buyer's domain with a generic business domain such as visitors, generic callers, or office reception.
- Each section should be 2-3 paragraphs maximum. Keep total proposal under 4000 words.
- Use professional business language.
- Return valid JSON only — no markdown fences, no extra text outside the JSON object.
"""

_configured = False


def _ensure_configured():
    global _configured
    if not _configured:
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        _configured = True


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "429" in message or "quota" in message or "rate" in message


def _parse_sections(raw: str, provider: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"{provider} did not return valid JSON.")


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


def retrieve_chunks_with_metrics(org_id: str, query_text: str, top_k: int | None = None) -> tuple[list, dict]:
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
        chunks_used.append({
            "chunk_id": cid,
            "document_id": chunk.metadata.get("document_id"),
            "source_title": chunk.metadata.get("source_title", "Unknown"),
            "category": chunk.metadata.get("category"),
            "vector_rank": vector_rank_by_id.get(cid),
            "rerank_score": rerank_meta["scores"].get(cid),
        })

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


def _build_prompts(context: str, rfp_text: str, tone: str = "professional", rfp_brief: dict | None = None) -> tuple[str, str]:
    # Use tone from Pass 1 analysis if not overridden
    if rfp_brief and tone == "professional":
        tone = rfp_brief.get("tone_preference", "professional")
    tone_instruction = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["professional"])
    system_prompt = (
        "You are an expert proposal writer for a professional services firm. "
        "You write highly tailored, technically accurate proposals based strictly on provided context. "
        f"TONE INSTRUCTION: {tone_instruction} "
        + SECTION_INSTRUCTIONS
    )

    brief_block = ""
    if rfp_brief:
        brief_block = (
            "RFP ANALYSIS (use this to guide every section):\n"
            f"- Client: {rfp_brief.get('client_name', 'Unknown')}\n"
            f"- Industry/Domain: {rfp_brief.get('industry', 'Unknown')}\n"
            f"- Compliance Requirements: {', '.join(rfp_brief.get('compliance_requirements', [])) or 'None stated'}\n"
            f"- Key Requirements: {'; '.join(rfp_brief.get('key_requirements', []))}\n"
            f"- Evaluation Criteria: {'; '.join(rfp_brief.get('evaluation_criteria', []))}\n"
            f"- Budget Signals: {rfp_brief.get('budget_signals', 'Not specified')}\n"
            f"- Timeline: {rfp_brief.get('timeline', 'Not specified')}\n"
            f"- Emphasized Sections: {', '.join(rfp_brief.get('emphasized_sections', []))}\n"
            f"- Red Flags / Must-Nots: {'; '.join(rfp_brief.get('red_flags', [])) or 'None'}\n\n"
        )

    user_message = (
        f"{brief_block}"
        f"CONTEXT FROM OUR HISTORICAL PROPOSALS AND CASE STUDIES:\n\n{context}\n\n"
        f"---\n\nNEW RFP / PROJECT BRIEF:\n\n{rfp_text}\n\n"
        "Generate the proposal JSON now."
    )
    return system_prompt, user_message


def _generate_with_gemini(system_prompt: str, user_message: str) -> dict:
    _ensure_configured()
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=system_prompt,
        generation_config={
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        },
    )

    response = model.generate_content(user_message)
    return _parse_sections(response.text, "Gemini")


def _generate_with_groq(system_prompt: str, user_message: str) -> dict:
    if not settings.GROQ_API_KEY:
        raise ValueError("Gemini hit a rate limit and GROQ_API_KEY is not configured.")

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens": 8192,
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
    return _parse_sections(raw, "Groq")


def _generate_with_fallbacks(system_prompt: str, user_message: str) -> tuple[str, dict]:
    """Try Claude (primary) → Gemini → Groq. Returns (provider_name, sections)."""
    import logging
    log = logging.getLogger(__name__)

    # Groq llama-3.1-8b free tier caps at 6k TPM — useless for our ~16k-token prompt.
    # Skip Groq entirely if prompt is bigger than the free-tier ceiling.
    approx_tokens = (len(system_prompt) + len(user_message)) // 4
    groq_usable = approx_tokens < 5500

    if settings.CLAUDE_ENABLED and settings.ANTHROPIC_API_KEY:
        try:
            sections = claude_provider.generate_proposal(system_prompt, user_message)
            return "claude", sections
        except Exception as exc:
            log.warning("Claude generation failed, falling back to Gemini: %s", exc)

    try:
        sections = _generate_with_gemini(system_prompt, user_message)
        return "gemini", sections
    except Exception as exc:
        if _is_rate_limit_error(exc) and groq_usable and settings.GROQ_API_KEY:
            log.warning("Gemini rate-limited, falling back to Groq: %s", exc)
            sections = _generate_with_groq(system_prompt, user_message)
            return "groq", sections
        raise


def generate_proposal_sync(rfp_text: str, org_id: str, tone: str = "professional") -> dict:
    """Two-pass proposal generation: analyze RFP first, then write using structured brief."""
    sections, _ = generate_proposal_with_metrics(rfp_text, org_id, tone)
    return sections


def generate_proposal_with_metrics(rfp_text: str, org_id: str, tone: str = "professional") -> tuple[dict, dict]:
    """
    Two-pass generation + telemetry.
    Returns (sections_dict, metrics_dict).
    metrics_dict shape matches GenerationEvent fields plus rfp_brief.
    """
    overall_started = time.perf_counter()

    try:
        rfp_brief = _analyze_rfp(rfp_text)
    except Exception:
        rfp_brief = {}

    chunks, retrieval_meta = retrieve_chunks_with_metrics(org_id, rfp_text)
    context = _format_context(chunks)
    system_prompt, user_message = _build_prompts(context, rfp_text, tone, rfp_brief=rfp_brief)

    gen_started = time.perf_counter()
    provider, sections = _generate_with_fallbacks(system_prompt, user_message)
    generation_latency_ms = int((time.perf_counter() - gen_started) * 1000)

    metrics = {
        **retrieval_meta,
        "provider": provider,
        "generation_latency_ms": generation_latency_ms,
        "total_latency_ms": int((time.perf_counter() - overall_started) * 1000),
        "rfp_brief": rfp_brief,
    }
    return sections, metrics
