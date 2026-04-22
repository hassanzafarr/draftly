from django.contrib import admin
from .models import Document, Chunk


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "org", "file_type", "status", "chunk_count", "created_at"]
    list_filter = ["status", "file_type"]
    search_fields = ["title"]


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ["id", "document", "org", "created_at"]
    raw_id_fields = ["document"]
