from datetime import datetime
from datetime import timezone as dt_timezone

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class PasswordAwareJWTAuthentication(JWTAuthentication):
    """Reject tokens issued before the user's most recent password change."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user.password_changed_at is not None:
            iat = validated_token.get("iat")
            if iat is not None:
                issued_at = datetime.fromtimestamp(iat, tz=dt_timezone.utc)
                if issued_at < user.password_changed_at:
                    raise InvalidToken("Token invalidated by password change.")
        return user
