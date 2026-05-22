import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Organization(models.Model):
    class Tier(models.TextChoices):
        FREE = "free", "Free"
        SOLO = "solo", "Solo"
        STUDIO = "studio", "Studio"
        AGENCY = "agency", "Agency"

    class BillingCadence(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    QUOTA = {
        "free": {"docs": 10, "proposals": 3, "seats": 1, "monthly_price_usd": 0, "annual_price_usd": 0},
        "solo": {"docs": 25, "proposals": 25, "seats": 1, "monthly_price_usd": 19, "annual_price_usd": 182},
        "studio": {"docs": 250, "proposals": 150, "seats": 5, "monthly_price_usd": 89, "annual_price_usd": 854},
        "agency": {"docs": 999999, "proposals": 750, "seats": 10, "monthly_price_usd": 249, "annual_price_usd": 2390},
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    subscription_tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.FREE)
    billing_cadence = models.CharField(max_length=10, choices=BillingCadence.choices, default=BillingCadence.MONTHLY)
    created_at = models.DateTimeField(auto_now_add=True)

    stripe_customer_id = models.CharField(max_length=255, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=255, blank=True, default="")
    subscription_status = models.CharField(max_length=50, blank=True, default="")
    current_period_end = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    @property
    def doc_quota(self):
        return self.QUOTA[self.subscription_tier]["docs"]

    @property
    def proposal_quota(self):
        return self.QUOTA[self.subscription_tier]["proposals"]

    @property
    def seat_limit(self):
        return self.QUOTA[self.subscription_tier]["seats"]

    @property
    def monthly_price_usd(self):
        return self.QUOTA[self.subscription_tier]["monthly_price_usd"]

    @property
    def annual_price_usd(self):
        return self.QUOTA[self.subscription_tier]["annual_price_usd"]


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
