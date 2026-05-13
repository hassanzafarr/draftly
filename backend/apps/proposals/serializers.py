from django.conf import settings
from rest_framework import serializers
from apps.documents.pipeline import extract_text
from .models import RFP, Proposal


ALLOWED_RFP_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class RFPSerializer(serializers.ModelSerializer):
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = RFP
        fields = ["id", "title", "raw_text", "created_by_email", "created_at"]
        read_only_fields = ["id", "created_at"]


class RFPCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500)
    raw_text = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField(required=False)

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
        return attrs


class ProposalSerializer(serializers.ModelSerializer):
    rfp_title = serializers.CharField(source="rfp.title", read_only=True)

    class Meta:
        model = Proposal
        fields = ["id", "rfp", "rfp_title", "tone", "sections", "status", "error_message", "created_at", "updated_at"]
        read_only_fields = ["id", "rfp", "status", "created_at", "updated_at"]


class ProposalUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposal
        fields = ["sections", "status"]

    def validate_status(self, value):
        allowed = [Proposal.Status.DRAFT, Proposal.Status.FINAL]
        if value not in allowed:
            raise serializers.ValidationError("Status can only be set to 'draft' or 'final'.")
        return value
