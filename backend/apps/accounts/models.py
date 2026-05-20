import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Organization(models.Model):
    class Tier(models.TextChoices):
        STARTER = "starter", "Starter"
        GROWTH = "growth", "Growth"
        AGENCY = "agency", "Agency"

    QUOTA = {
        "starter": {"docs": 50, "proposals": 5},
        "growth": {"docs": 200, "proposals": 25},
        "agency": {"docs": 999999, "proposals": 999999},
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    subscription_tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.STARTER)
    created_at = models.DateTimeField(auto_now_add=True)

    # Stripe billing
    stripe_customer_id = models.CharField(max_length=255, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=255, blank=True, default="")
    subscription_status = models.CharField(max_length=50, blank=True, default="")
    current_period_end = models.DateTimeField(null=True, blank=True)

    # Credits — consumed only after monthly quota is exhausted; never reset monthly
    credit_balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    def consume_credit(self):
        """Atomically deduct 1 credit. Called only on successful proposal generation."""
        Organization.objects.filter(pk=self.pk, credit_balance__gt=0).update(
            credit_balance=models.F("credit_balance") - 1
        )

    @property
    def doc_quota(self):
        return self.QUOTA[self.subscription_tier]["docs"]

    @property
    def proposal_quota(self):
        return self.QUOTA[self.subscription_tier]["proposals"]


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="users", null=True, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
