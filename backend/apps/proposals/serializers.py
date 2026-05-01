from rest_framework import serializers
from .models import RFP, Proposal


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

    def validate(self, attrs):
        if not attrs.get("raw_text", "").strip() and not attrs.get("file"):
            raise serializers.ValidationError("Provide RFP text or upload an RFP file.")
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
