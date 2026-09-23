from django.contrib import admin

from .models import MCPToken


@admin.register(MCPToken)
class MCPTokenAdmin(admin.ModelAdmin):
    list_display = ["token_prefix", "org", "name", "created_at", "revoked_at", "last_used_at"]
    list_filter = ["revoked_at"]
    search_fields = ["org__name", "token_prefix", "name"]
    readonly_fields = ["id", "token_hash", "token_prefix", "created_at", "last_used_at"]
