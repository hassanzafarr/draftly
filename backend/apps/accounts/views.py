import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.permissions import IsOrgAdmin, IsOrgMember
from apps.core.throttling import (
    AuthLoginThrottle,
    AuthRegisterThrottle,
    PasswordChangeThrottle,
    PasswordResetThrottle,
    TeamInviteThrottle,
)

from .models import Invitation, Organization, User
from .serializers import (
    InvitationSerializer,
    InviteAcceptSerializer,
    OrganizationSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    TeamMemberSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


class GoogleAwareTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Reject email+password login attempts for Google-only accounts with a clear message."""

    def validate(self, attrs):
        email = attrs.get(self.username_field, "")
        try:
            user = User.objects.get(email=email)
            if user.google_id and not user.has_usable_password():
                raise drf_serializers.ValidationError(
                    "This account uses Google Sign-In. Please use the Google button to sign in."
                )
        except User.DoesNotExist:
            pass
        return super().validate(attrs)


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """JWT login with brute-force throttling and a clear error for unverified accounts."""

    serializer_class = GoogleAwareTokenObtainPairSerializer
    throttle_classes = [AuthLoginThrottle]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email", "").strip().lower()
        try:
            user = User.objects.get(email__iexact=email)
            if not user.is_active and user.check_password(request.data.get("password", "")):
                return Response(
                    {"detail": "Please verify your email address before logging in."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except User.DoesNotExist:
            pass
        return super().post(request, *args, **kwargs)


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

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_url = f"{settings.FRONTEND_URL}/verify-email?uid={uid}&token={token}"
    try:
        send_mail(
            subject="Verify your Draftly email",
            message=(
                f"Hi,\n\n"
                f"Thanks for signing up. Click the link below to verify your email address.\n\n"
                f"{verify_url}\n\n"
                f"If you didn't create this account, you can ignore this email.\n\n"
                f"— Draftly"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send verification email to %s", user.email)

    return Response(
        {**UserSerializer(user).data, "detail": "Check your email to verify your account."},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_email(request):
    """Activate a user account using the uid+token from the verification email."""
    uid = request.data.get("uid", "")
    token = request.data.get("token", "")

    try:
        pk = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=pk)
    except (User.DoesNotExist, ValueError, TypeError):
        return Response(
            {"detail": "Invalid verification link."}, status=status.HTTP_400_BAD_REQUEST
        )

    if user.is_active:
        return Response({"detail": "Account already verified."})

    if not default_token_generator.check_token(user, token):
        return Response(
            {"detail": "Verification link is invalid or has expired."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.is_active = True
    user.save(update_fields=["is_active"])
    return Response({"detail": "Email verified. You can now log in."})


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
        if User.objects.filter(email=email).exclude(pk=user.pk).exists():
            return Response(
                {"detail": "Email already in use."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.email = email
        user.save(update_fields=["email"])
        org = user.org
        if org and org.stripe_customer_id:
            try:
                import stripe

                stripe.api_key = settings.STRIPE_SECRET_KEY
                stripe.Customer.modify(org.stripe_customer_id, email=email)
            except Exception:
                logger.warning("Could not sync email to Stripe customer %s", org.stripe_customer_id)
    return Response(UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([PasswordChangeThrottle])
def change_password(request):
    """Change the authenticated user's password and invalidate existing JWTs."""
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
    user.password_changed_at = timezone.now()
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
    except User.DoesNotExist:
        user = None  # don't reveal whether email exists

    if user is not None:
        try:
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
                fail_silently=False,
            )
        except Exception:
            logger.exception("Failed to send password reset email to %s", email)

    return Response({"detail": "If that email is registered, a reset link has been sent."})


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """Validate the reset token, set the new password, and invalidate existing JWTs."""
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
        return Response(
            {"detail": "Reset link is invalid or has expired."}, status=status.HTTP_400_BAD_REQUEST
        )

    user.set_password(new_password)
    user.password_changed_at = timezone.now()
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


def _org_seats_used(org):
    """Seats consumed = existing users + pending non-expired invites."""
    pending_invites = _active_pending_invites(org).count()
    return org.users.count() + pending_invites


def _active_pending_invites(org):
    """Pending invitations that can still be accepted."""
    return Invitation.objects.filter(
        org=org, status=Invitation.Status.PENDING, expires_at__gt=timezone.now()
    )


@api_view(["GET"])
@permission_classes([IsOrgMember])
def team_members(request):
    """List all users in the caller's organization."""
    members = User.objects.filter(org=request.user.org).order_by("created_at")
    return Response(
        {
            "members": TeamMemberSerializer(members, many=True).data,
            "seats_used": _org_seats_used(request.user.org),
            "seat_limit": request.user.org.seat_limit,
        }
    )


@api_view(["DELETE"])
@permission_classes([IsOrgAdmin])
def team_member_detail(request, pk):
    """Remove a member from the organization (admin only, cannot remove yourself)."""
    try:
        member = User.objects.get(pk=pk, org=request.user.org)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if member.pk == request.user.pk:
        return Response(
            {"detail": "You cannot remove yourself from the organization."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    member.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
@permission_classes([IsOrgAdmin])
@throttle_classes([TeamInviteThrottle])
def team_invites(request):
    """List pending invites or create a new one (admin only)."""
    org = request.user.org

    if request.method == "GET":
        invites = _active_pending_invites(org)
        return Response(InvitationSerializer(invites, many=True).data)

    serializer = InvitationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"].strip().lower()
    role = serializer.validated_data.get("role", User.Role.MEMBER)

    if User.objects.filter(email__iexact=email).exists():
        return Response(
            {"detail": "A user with this email already has a Draftly account."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if _active_pending_invites(org).filter(email__iexact=email).exists():
        return Response(
            {"detail": "An invitation for this email is already pending."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if _org_seats_used(org) >= org.seat_limit:
        return Response(
            {
                "detail": (
                    f"Seat limit reached ({org.seat_limit} seats on the "
                    f"{org.get_subscription_tier_display()} plan). "
                    "Upgrade your plan to invite more teammates."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    invite = Invitation.objects.create(org=org, email=email, role=role, invited_by=request.user)
    accept_url = f"{settings.FRONTEND_URL}/accept-invite?token={invite.token}"
    try:
        send_mail(
            subject=f"You've been invited to join {org.name} on Draftly",
            message=(
                f"Hi,\n\n"
                f"{request.user.email} has invited you to join {org.name} on Draftly.\n\n"
                f"Click the link below to accept the invitation and set up your account. "
                f"This link expires in {Invitation.TTL_DAYS} days.\n\n"
                f"{accept_url}\n\n"
                f"If you weren't expecting this invitation, you can ignore this email.\n\n"
                f"— Draftly"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send invitation email to %s", email)
        invite.delete()
        return Response(
            {"detail": "Could not send the invitation email. Please try again."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response(InvitationSerializer(invite).data, status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([IsOrgAdmin])
def team_invite_detail(request, pk):
    """Revoke a pending invitation (admin only)."""
    try:
        invite = Invitation.objects.get(
            pk=pk, org=request.user.org, status=Invitation.Status.PENDING
        )
    except Invitation.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    invite.status = Invitation.Status.REVOKED
    invite.save(update_fields=["status"])
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([AllowAny])
def invite_info(request, token):
    """Public lookup of an invitation by token, for the accept-invite page."""
    try:
        invite = Invitation.objects.select_related("org", "invited_by").get(token=token)
    except Invitation.DoesNotExist:
        return Response({"detail": "Invitation not found."}, status=status.HTTP_404_NOT_FOUND)

    if invite.status != Invitation.Status.PENDING:
        return Response(
            {"detail": "This invitation is no longer valid."},
            status=status.HTTP_410_GONE,
        )
    if invite.is_expired:
        return Response({"detail": "This invitation has expired."}, status=status.HTTP_410_GONE)

    return Response(
        {
            "email": invite.email,
            "org_name": invite.org.name,
            "role": invite.role,
            "invited_by": invite.invited_by.email if invite.invited_by else None,
            "expires_at": invite.expires_at,
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthRegisterThrottle])
def invite_accept(request):
    """Accept an invitation: create the user in the inviting org and log them in."""
    serializer = InviteAcceptSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        invite = Invitation.objects.select_related("org").get(
            token=serializer.validated_data["token"]
        )
    except Invitation.DoesNotExist:
        return Response({"detail": "Invitation not found."}, status=status.HTTP_404_NOT_FOUND)

    if invite.status != Invitation.Status.PENDING or invite.is_expired:
        return Response(
            {"detail": "This invitation is no longer valid."},
            status=status.HTTP_410_GONE,
        )
    if User.objects.filter(email__iexact=invite.email).exists():
        return Response(
            {"detail": "This email is already registered. Please sign in instead."},
            status=status.HTTP_409_CONFLICT,
        )
    # Seats may have filled up between invite creation and acceptance.
    if invite.org.users.count() >= invite.org.seat_limit:
        return Response(
            {"detail": "This organization has no seats available. Ask your admin to upgrade."},
            status=status.HTTP_403_FORBIDDEN,
        )

    with transaction.atomic():
        # Email ownership is proven by possession of the invite token,
        # so the account is active immediately — no verification email.
        user = User.objects.create_user(
            email=invite.email,
            password=serializer.validated_data["password"],
            org=invite.org,
            role=invite.role,
            is_active=True,
            terms_accepted_at=timezone.now(),
        )
        invite.status = Invitation.Status.ACCEPTED
        invite.accepted_at = timezone.now()
        invite.save(update_fields=["status", "accepted_at"])

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        },
        status=status.HTTP_201_CREATED,
    )


def _verify_google_access_token(access_token):
    """
    Verify a Google OAuth access token and return normalised user info.

    Calls Google's tokeninfo endpoint to confirm the token belongs to this app,
    then calls the userinfo endpoint for the full profile.
    Raises ValueError if the token is invalid or not issued for this app.
    """
    import json
    import urllib.error
    import urllib.parse
    import urllib.request

    # 1. Verify the token is valid and issued for our Client ID.
    tokeninfo_url = "https://oauth2.googleapis.com/tokeninfo?" + urllib.parse.urlencode(
        {"access_token": access_token}
    )
    try:
        with urllib.request.urlopen(tokeninfo_url, timeout=5) as resp:
            token_data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise ValueError("Invalid Google access token") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ValueError("Could not reach Google to verify the token. Please try again.") from exc

    client_id = settings.GOOGLE_CLIENT_ID
    if client_id and token_data.get("azp") != client_id and token_data.get("aud") != client_id:
        raise ValueError("Google token not issued for this application")

    if str(token_data.get("email_verified", "")).lower() != "true":
        raise ValueError("Google email is not verified")

    # 2. Fetch the full profile (given_name, picture, etc.).
    userinfo_req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with urllib.request.urlopen(userinfo_req, timeout=5) as resp:
            userinfo = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise ValueError("Could not fetch Google profile") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ValueError("Could not reach Google to fetch your profile. Please try again.") from exc

    return {
        "sub": token_data.get("sub") or userinfo.get("sub"),
        "email": userinfo.get("email") or token_data.get("email"),
        "email_verified": True,
        "given_name": userinfo.get("given_name", ""),
        "picture": userinfo.get("picture", ""),
    }


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthLoginThrottle])
def google_auth(request):
    """
    Step 1 of Google sign-in.

    Returns one of three outcomes:
    - { access, refresh, user }       — existing Google user, logged in
    - { status: "new_user", email, display_name } — new user, needs org name
    - 409 with detail                 — email already registered via password
    """
    credential = request.data.get("credential")
    if not credential:
        return Response({"detail": "credential is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        idinfo = _verify_google_access_token(credential)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    email = idinfo["email"]
    google_id = idinfo["sub"]
    avatar = idinfo.get("picture", "")
    display_name = idinfo.get("given_name") or email.split("@")[0]

    # Returning Google user
    user = User.objects.filter(google_id=google_id).first()
    if user:
        if avatar and user.avatar_url != avatar:
            user.avatar_url = avatar
            user.save(update_fields=["avatar_url"])
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            }
        )

    # Email already registered via password — hard block
    if User.objects.filter(email=email, google_id__isnull=True).exists():
        return Response(
            {"detail": "This email is already registered. Please sign in with your password."},
            status=status.HTTP_409_CONFLICT,
        )

    # Brand-new user — ask frontend to collect org name
    return Response(
        {
            "status": "new_user",
            "email": email,
            "display_name": display_name,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthRegisterThrottle])
def google_auth_complete(request):
    """
    Step 2 of Google sign-in for new users.

    Accepts { credential, org_name }, re-verifies the Google token,
    creates the org + user, and returns JWT tokens.
    """
    credential = request.data.get("credential")
    org_name = request.data.get("org_name", "").strip()

    if not credential:
        return Response({"detail": "credential is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not org_name or len(org_name) < 2:
        return Response(
            {"detail": "Please enter your organisation name (at least 2 characters)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        idinfo = _verify_google_access_token(credential)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    email = idinfo["email"]
    google_id = idinfo["sub"]
    avatar = idinfo.get("picture", "")

    # Guard: email registered with password in the window between step 1 and step 2
    if User.objects.filter(email=email, google_id__isnull=True).exists():
        return Response(
            {"detail": "This email is already registered. Please sign in with your password."},
            status=status.HTTP_409_CONFLICT,
        )

    # Guard: already completed (e.g. double-submit)
    existing = User.objects.filter(google_id=google_id).first()
    if existing:
        refresh = RefreshToken.for_user(existing)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(existing).data,
            }
        )

    with transaction.atomic():
        org = Organization.objects.create(name=org_name)
        user = User(
            email=email,
            google_id=google_id,
            avatar_url=avatar or None,
            org=org,
            role=User.Role.ADMIN,
            terms_accepted_at=timezone.now(),
        )
        user.set_unusable_password()
        user.save()

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        },
        status=status.HTTP_201_CREATED,
    )
