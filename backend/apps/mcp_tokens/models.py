import hashlib
import secrets
import uuid

from django.db import models
from django.db.models.functions import Now

from apps.accounts.models import Organization


def _hash_token(plaintext):
    return hashlib.sha256(plaintext.encode()).hexdigest()


class MCPToken(models.Model):
    """Bearer credential for a single org, used by the standalone MCP server.

    Only the SHA-256 hash of the secret is ever stored. The plaintext is
    returned once, at creation time, and cannot be recovered afterward.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="mcp_tokens")
    name = models.CharField(max_length=255, blank=True, default="")
    token_hash = models.CharField(max_length=64, unique=True)
    token_prefix = models.CharField(max_length=12)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["token_hash"])]
        ordering = ["-created_at"]

    def __str__(self):
        state = "revoked" if self.revoked_at else "active"
        return f"MCPToken {self.token_prefix}… ({self.org.name}, {state})"

    @classmethod
    def generate(cls, org, name=""):
        """Create a token for `org`. Returns (instance, plaintext_secret) —
        the plaintext is only ever available here, at creation time."""
        plaintext = secrets.token_urlsafe(32)
        instance = cls.objects.create(
            org=org,
            name=name,
            token_hash=_hash_token(plaintext),
            token_prefix=plaintext[:8],
        )
        return instance, plaintext

    @classmethod
    def resolve(cls, plaintext):
        """Look up an active token by its plaintext secret. Returns the
        instance and bumps last_used_at, or None if missing/revoked."""
        try:
            token = cls.objects.select_related("org").get(
                token_hash=_hash_token(plaintext), revoked_at__isnull=True
            )
        except cls.DoesNotExist:
            return None
        cls.objects.filter(pk=token.pk).update(last_used_at=Now())
        return token
