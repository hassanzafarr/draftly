import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from django.conf import settings
from apps.core.throttling import AuthLoginThrottle, AuthRegisterThrottle, PasswordChangeThrottle, PasswordResetThrottle
from .serializers import RegisterSerializer, UserSerializer, OrganizationSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer
from .models import Organization, User


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """JWT login endpoint with per-IP brute-force throttling."""
    throttle_classes = [AuthLoginThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    """JWT refresh — uses default user/anon rates."""
    pass


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthRegisterThrottle])
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
        # Keep Stripe customer in sync so receipts go to the right address.
        org = user.org
        if org and org.stripe_customer_id:
            try:
                import stripe
                stripe.api_key = settings.STRIPE_SECRET_KEY
                stripe.Customer.modify(org.stripe_customer_id, email=email)
            except Exception:
                logger.warning(
                    "Could not sync email to Stripe customer %s", org.stripe_customer_id
                )
    return Response(UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([PasswordChangeThrottle])
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


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetThrottle])
def password_reset_request(request):
    """Send a password reset link to the given email if it exists."""
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"]

    try:
        user = User.objects.get(email=email)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
        send_mail(
            subject="Reset your Draftly password",
            message=(
                f"Hi,\n\n"
                f"Click the link below to reset your password. "
                f"This link expires in 1 hour.\n\n"
                f"{reset_url}\n\n"
                f"If you didn't request this, ignore this email.\n\n"
                f"— Draftly"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
    except User.DoesNotExist:
        pass  # don't reveal whether email exists

    return Response({"detail": "If that email is registered, a reset link has been sent."})


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """Validate the reset token and set the new password."""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    uid = serializer.validated_data["uid"]
    token = serializer.validated_data["token"]
    new_password = serializer.validated_data["new_password"]

    try:
        pk = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=pk)
    except (User.DoesNotExist, ValueError, TypeError):
        return Response({"detail": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

    if not default_token_generator.check_token(user, token):
        return Response({"detail": "Reset link is invalid or has expired."}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()
    return Response({"detail": "Password reset successfully."})


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

