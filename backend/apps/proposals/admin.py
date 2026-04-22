from django.contrib import admin
from .models import RFP, Proposal


@admin.register(RFP)
class RFPAdmin(admin.ModelAdmin):
    list_display = ["title", "org", "created_by", "created_at"]
    search_fields = ["title"]


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ["rfp", "org", "status", "created_at"]
    list_filter = ["status"]
