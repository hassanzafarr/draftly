from django.contrib import admin

from .models import RFP, GenerationEvent, Proposal, Template


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "org", "is_active", "sort_order", "created_at"]
    list_filter = ["category", "is_active"]
    search_fields = ["title", "org__name"]


@admin.register(RFP)
class RFPAdmin(admin.ModelAdmin):
    list_display = ["title", "org", "created_by", "created_at"]
    search_fields = ["title"]


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ["rfp", "org", "status", "created_at"]
    list_filter = ["status"]


@admin.register(GenerationEvent)
class GenerationEventAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "org",
        "provider",
        "rerank_used",
        "requirements_coverage",
        "red_flags_coverage",
        "total_latency_ms",
        "success",
    ]
    list_filter = ["success", "rerank_used", "provider", "org"]
    readonly_fields = [
        "proposal",
        "org",
        "fetch_top_k",
        "rerank_top_k",
        "rerank_used",
        "rerank_latency_ms",
        "retrieval_latency_ms",
        "chunks_used",
        "provider",
        "generation_latency_ms",
        "total_latency_ms",
        "rfp_brief",
        "requirements_total",
        "requirements_hit",
        "red_flags_total",
        "red_flags_hit",
        "section_word_counts",
        "success",
        "error_message",
        "created_at",
    ]
