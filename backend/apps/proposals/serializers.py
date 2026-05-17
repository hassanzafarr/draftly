import logging
import re
from datetime import date
from django.conf import settings
from rest_framework import serializers
from apps.documents.pipeline import extract_text
from .models import RFP, Proposal

log = logging.getLogger(__name__)


ALLOWED_RFP_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _llm_title(text: str) -> str:
    """Try Claude then Gemini to get a clean 3-7 word title. Returns '' on failure."""
    snippet = text[:400]

    # 1. Claude (primary)
    if settings.CLAUDE_ENABLED and settings.ANTHROPIC_API_KEY:
        try:
            from . import claude_provider
            title = claude_provider.generate_title(snippet)
            if title and 3 <= len(title) <= 120:
                return title
        except Exception as exc:
            log.warning("Claude title generation failed: %s", exc)

    # 2. Gemini (secondary)
    try:
        from .generator import generate_title_with_gemini
        title = generate_title_with_gemini(snippet)
        if title and 3 <= len(title) <= 120:
            return title
    except Exception as exc:
        log.warning("Gemini title generation failed: %s", exc)

    return ""


def _heuristic_title(text: str) -> str:
    """
    Regex heuristics in order of confidence:
      1. Explicit label  — "Title: ...", "Subject: ...", "Project Name: ..."
      2. Common phrases  — "RFP for ...", "proposal for ..."
      3. First short line — if the opening line is ≤ 80 chars and looks like a title
      4. First sentence   — up to 80 chars, trimmed at last word boundary
    Returns '' if nothing suitable found.
    """
    if not text:
        return ""

    sample = " ".join(text.split()[:120])

    # 1. Explicit label patterns
    for pat in [r"(?:project\s+name|title|subject|rfp\s+title)\s*[:\-]\s*([^\n\.]{3,80})"]:
        m = re.search(pat, sample, re.IGNORECASE)
        if m:
            return _clean(m.group(1))

    # 2. Phrase patterns
    for pat in [
        r"request\s+for\s+proposal\s+for\s+([^\n\.]{3,80})",
        r"rfp\s+for\s+([^\n\.]{3,80})",
        r"proposal\s+for\s+(?:a\s+|an\s+|the\s+)?([^\n\.]{3,80})",
        r"i\s+need\s+a\s+proposal\s+for\s+(?:a\s+|an\s+|the\s+)?([^\n\.]{3,80})",
    ]:
        m = re.search(pat, sample, re.IGNORECASE)
        if m:
            candidate = _clean(m.group(1))
            candidate = re.split(
                r"\s+(?:that|which|this|where|and|to|with|including|\.|,)",
                candidate, flags=re.IGNORECASE
            )[0].strip()
            if len(candidate) >= 5:
                return _capitalise(candidate)

    # 3. First non-empty line — only if it looks like a title (≤ 60 chars, no verb-ish sentences)
    for line in text.splitlines():
        line = line.strip()
        if 5 <= len(line) <= 60 and not line.startswith(("http", "www")):
            # Skip lines that are clearly a prose sentence (contain a period mid-line)
            if "." not in line and "," not in line:
                return _capitalise(line)

    return ""


def extract_title_from_rfp(text: str) -> str:
    """
    Option C title chain:
      1. LLM (Claude → Gemini)   — smart, context-aware
      2. Regex heuristics         — fast, deterministic
      3. Date-stamped fallback    — always succeeds
    """
    # Tier 1 — LLM
    title = _llm_title(text)
    if title:
        return title

    # Tier 2 — heuristics
    title = _heuristic_title(text)
    if title:
        return title

    # Tier 3 — safe fallback
    return f"Proposal \u2014 {date.today().strftime('%b %d, %Y')}"


def _clean(s: str) -> str:
    """Strip surrounding punctuation and whitespace."""
    return re.sub(r"[\s,;:]+$", "", s.strip())


def _capitalise(s: str) -> str:
    """Title-case the first word, leave the rest as-is."""
    if not s:
        return s
    return s[0].upper() + s[1:]


class RFPSerializer(serializers.ModelSerializer):
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = RFP
        fields = ["id", "title", "raw_text", "sections", "created_by_email", "created_at"]
        read_only_fields = ["id", "created_at"]


class RFPCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500, required=False, allow_blank=True)
    raw_text = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField(required=False)
    sections = serializers.ListField(
        child=serializers.CharField(max_length=120, allow_blank=False),
        required=False,
        allow_empty=True,
    )

    def validate_file(self, file):
        if not file:
            return file
        ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
        if ext not in ALLOWED_RFP_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file type '.{ext}'. Allowed: pdf, docx, txt."
            )
        if file.size == 0:
            raise serializers.ValidationError("Uploaded file is empty.")
        if file.size > MAX_FILE_SIZE_BYTES:
            raise serializers.ValidationError("File exceeds 10 MB limit.")
        return file

    def validate(self, attrs):
        raw_text = attrs.get("raw_text", "").strip()
        file = attrs.get("file")

        if not raw_text and not file:
            raise serializers.ValidationError(
                {"detail": "Provide RFP text or upload an RFP file."}
            )

        extracted_text = ""
        if file:
            ext = file.name.rsplit(".", 1)[-1].lower()
            try:
                extracted_text = extract_text(file.read(), ext).strip()
            except Exception as exc:
                raise serializers.ValidationError(
                    {"detail": f"Could not read file: {exc}"}
                ) from exc
            finally:
                file.seek(0)

            if not extracted_text:
                raise serializers.ValidationError(
                    {"detail": "File appears empty or image-only. Scanned PDFs without OCR are not supported — paste the RFP text instead."}
                )

        if raw_text and extracted_text:
            resolved = f"{raw_text}\n\n--- ATTACHED RFP FILE TEXT ---\n\n{extracted_text}"
        else:
            resolved = raw_text or extracted_text

        resolved_stripped = resolved.strip()
        char_count = len(resolved_stripped)
        word_count = len(resolved_stripped.split())

        if char_count < settings.RFP_MIN_CHARS:
            raise serializers.ValidationError(
                {"detail": (
                    f"RFP content too short ({char_count} chars). "
                    f"Provide at least {settings.RFP_MIN_CHARS} characters describing scope and requirements."
                )}
            )
        if word_count < settings.RFP_MIN_WORDS:
            raise serializers.ValidationError(
                {"detail": (
                    f"RFP content too short ({word_count} words). "
                    f"Provide at least {settings.RFP_MIN_WORDS} words describing scope and requirements."
                )}
            )
        if char_count > settings.RFP_MAX_CHARS:
            raise serializers.ValidationError(
                {"detail": f"RFP content too large ({char_count} chars). Max {settings.RFP_MAX_CHARS}."}
            )

        attrs["resolved_text"] = resolved

        # Auto-derive title if the client didn't supply one
        if not attrs.get("title", "").strip():
            attrs["title"] = extract_title_from_rfp(resolved_stripped)

        return attrs


class ProposalSerializer(serializers.ModelSerializer):
    rfp_title = serializers.CharField(source="rfp.title", read_only=True)

    class Meta:
        model = Proposal
        fields = [
            "id", "rfp", "rfp_title", "tone", "length", "sections", "section_labels", "status",
            "status_stage", "stage_meta", "error_message",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "rfp", "length", "section_labels", "status", "status_stage", "stage_meta",
            "created_at", "updated_at",
        ]


class ProposalUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposal
        fields = ["sections", "status"]

    def validate_status(self, value):
        allowed = [Proposal.Status.DRAFT, Proposal.Status.FINAL]
        if value not in allowed:
            raise serializers.ValidationError("Status can only be set to 'draft' or 'final'.")
        return value
