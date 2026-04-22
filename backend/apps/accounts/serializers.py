from rest_framework import serializers
from .models import Organization, User


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "subscription_tier", "doc_quota", "proposal_quota", "created_at"]
        read_only_fields = ["id", "created_at", "doc_quota", "proposal_quota"]


class UserSerializer(serializers.ModelSerializer):
    org = OrganizationSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "role", "org", "created_at"]
        read_only_fields = ["id", "created_at"]


class RegisterSerializer(serializers.Serializer):
    org_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def create(self, validated_data):
        org = Organization.objects.create(name=validated_data["org_name"])
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            org=org,
            role=User.Role.ADMIN,
        )
        return user
