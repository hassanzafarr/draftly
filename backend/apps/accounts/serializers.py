from django.utils import timezone
from rest_framework import serializers

from .models import Organization, User


class OrganizationSerializer(serializers.ModelSerializer):
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
        ]


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
