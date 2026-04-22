from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "subscription_tier", "created_at"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "role", "org", "is_active"]
    list_filter = ["role", "is_active"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Info", {"fields": ("org", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (None, {"fields": ("email", "password1", "password2", "org", "role")}),
    )
    ordering = ["email"]
    search_fields = ["email"]
