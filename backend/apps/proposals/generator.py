import anthropic
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
- Base all facts, client names, numbers, and case studies ONLY on the provided context chunks.
- Each section should be 2-4 detailed paragraphs.
- Use professional business language.
- Return valid JSON only — no markdown fences, no extra text outside the JSON object.
"""


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


def generate_proposal_sync(rfp_text: str, org_id: str) -> dict:
    """Retrieve context and call Claude. Returns parsed sections dict."""
    import json

    context = retrieve_context(org_id, rfp_text)

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_prompt = (
        "You are an expert proposal writer for a professional services firm. "
        "You write highly tailored, technically accurate proposals based strictly on provided context. "
        + SECTION_INSTRUCTIONS
    )

    user_message = (
        f"CONTEXT FROM OUR HISTORICAL PROPOSALS AND CASE STUDIES:\n\n{context}\n\n"
        f"---\n\nNEW RFP / PROJECT BRIEF:\n\n{rfp_text}\n\n"
        "Generate the proposal JSON now."
    )

    message = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = message.content[0].text
    try:
        sections = json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            sections = json.loads(match.group())
        else:
            raise ValueError("Claude did not return valid JSON.")

    return sections
