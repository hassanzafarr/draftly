import calendar
import datetime

from django.utils import timezone
from rest_framework import serializers

from .models import Organization, User


def _billing_period_start(period_end, cadence):
    if cadence == "annual":
        try:
            return period_end.replace(year=period_end.year - 1)
        except ValueError:
            return period_end.replace(year=period_end.year - 1, day=28)
    if period_end.month == 1:
        year, month = period_end.year - 1, 12
    else:
        year, month = period_end.year, period_end.month - 1
    max_day = calendar.monthrange(year, month)[1]
    return period_end.replace(year=year, month=month, day=min(period_end.day, max_day))


class OrganizationSerializer(serializers.ModelSerializer):
    proposals_used = serializers.SerializerMethodField()
    docs_used = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "subscription_tier",
            "billing_cadence",
            "subscription_status",
            "current_period_end",
            "doc_quota",
            "proposal_quota",
            "seat_limit",
            "monthly_price_usd",
            "annual_price_usd",
            "created_at",
            "proposals_used",
            "docs_used",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "subscription_status",
            "current_period_end",
            "doc_quota",
            "proposal_quota",
            "seat_limit",
            "monthly_price_usd",
            "annual_price_usd",
            "proposals_used",
            "docs_used",
        ]

    def get_proposals_used(self, obj):
        from apps.proposals.models import Proposal
        now = datetime.datetime.now(datetime.UTC)
        if obj.subscription_tier != "free" and obj.current_period_end:
            period_start = _billing_period_start(obj.current_period_end, obj.billing_cadence)
        else:
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return Proposal.objects.filter(org=obj, created_at__gte=period_start).count()

    def get_docs_used(self, obj):
        from apps.documents.models import Document
        return Document.objects.filter(org=obj, status="processed").count()


class UserSerializer(serializers.ModelSerializer):
    org = OrganizationSerializer(read_only=True)
    has_password = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "role", "org", "created_at", "avatar_url", "has_password"]
        read_only_fields = ["id", "created_at", "avatar_url", "has_password"]

    def get_has_password(self, obj):
        return obj.has_usable_password()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)


class RegisterSerializer(serializers.Serializer):
    org_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    terms_accepted = serializers.BooleanField(default=False)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def validate_terms_accepted(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the Terms of Service.")
        return value

    def create(self, validated_data):
        org = Organization.objects.create(name=validated_data["org_name"])
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            org=org,
            role=User.Role.ADMIN,
            is_active=False,  # activated via email verification link
            terms_accepted_at=timezone.now(),
        )
        return user
