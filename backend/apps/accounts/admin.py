from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Invitation, Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "subscription_tier", "billing_cadence", "created_at"]
    list_filter = ["subscription_tier", "billing_cadence"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "role", "org", "is_active"]
    list_filter = ["role", "is_active"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Info", {"fields": ("org", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = ((None, {"fields": ("email", "password1", "password2", "org", "role")}),)
    ordering = ["email"]
    search_fields = ["email"]


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "org", "role", "status", "created_at", "expires_at"]
    list_filter = ["status", "role"]
    search_fields = ["email", "org__name"]
