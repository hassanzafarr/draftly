import json
import re
from urllib import error, request
import google.generativeai as genai
from django.conf import settings
from pgvector.django import CosineDistance
from apps.documents.models import Chunk
from apps.core.embeddings import embed_text

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
- Mirror the buyer's industry, terminology, compliance needs, must-have features, and explicit instructions.
- If the RFP is healthcare, mental health, finance, legal, or another regulated field, include the relevant compliance and safety requirements throughout the proposal.
- Do not replace the buyer's domain with a generic business domain such as visitors, generic callers, or office reception.
- Each section should be 2-4 detailed paragraphs.
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


def retrieve_context(org_id: str, query_text: str, top_k: int = 20) -> str:
    query_vector = embed_text(query_text)
    chunks = (
        Chunk.objects.filter(org_id=org_id)
        .annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance")[:top_k]
    )
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.metadata.get("source_title", "Unknown")
        parts.append(f"[Source {i}: {source}]\n{chunk.content}")
    return "\n\n---\n\n".join(parts)


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
    """Pass 1: extract structured understanding of the RFP before writing."""
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


def generate_proposal_sync(rfp_text: str, org_id: str, tone: str = "professional") -> dict:
    """Two-pass proposal generation: analyze RFP first, then write using structured brief."""
    # Pass 1: analyze RFP — extract domain, compliance, scoring criteria, red flags
    try:
        rfp_brief = _analyze_rfp(rfp_text)
    except Exception:
        rfp_brief = {}  # non-fatal — degrade to single-pass if analysis fails

    # Pass 2: retrieve context + generate proposal informed by Pass 1 brief
    context = retrieve_context(org_id, rfp_text)
    system_prompt, user_message = _build_prompts(context, rfp_text, tone, rfp_brief=rfp_brief)

    try:
        return _generate_with_gemini(system_prompt, user_message)
    except Exception as exc:
        if _is_rate_limit_error(exc):
            return _generate_with_groq(system_prompt, user_message)
        raise
