from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.CharField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id", "title", "file_type", "status", "chunk_count",
            "error_message", "uploaded_by_email", "created_at",
        ]
        read_only_fields = ["id", "status", "chunk_count", "error_message", "created_at"]


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    title = serializers.CharField(max_length=500, required=False)

    def validate_file(self, value):
        ext = value.name.rsplit(".", 1)[-1].lower()
        if ext not in ("pdf", "docx", "txt"):
            raise serializers.ValidationError("Only PDF, DOCX, and TXT files are supported.")
        return value
