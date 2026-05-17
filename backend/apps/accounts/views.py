from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .serializers import RegisterSerializer, UserSerializer, OrganizationSerializer
from .models import Organization


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update user email (display name derived from email)."""
    user = request.user
    email = request.data.get("email")
    if email:
        from .models import User
        if User.objects.filter(email=email).exclude(pk=user.pk).exists():
            return Response(
                {"detail": "Email already in use."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.email = email
        user.save(update_fields=["email"])
    return Response(UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change the authenticated user's password."""
    user = request.user
    current = request.data.get("current_password", "")
    new = request.data.get("new_password", "")

    if not user.check_password(current):
        return Response(
            {"detail": "Current password is incorrect."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(new) < 8:
        return Response(
            {"detail": "New password must be at least 8 characters."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new)
    user.save()
    return Response({"detail": "Password changed successfully."})


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def org_settings(request):
    """Get or update organization details."""
    org = request.user.org
    if not org:
        return Response(
            {"detail": "No organization found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        return Response(OrganizationSerializer(org).data)

    name = request.data.get("name")
    if name:
        org.name = name
        org.save(update_fields=["name"])
    return Response(OrganizationSerializer(org).data)

