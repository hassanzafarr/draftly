from django.contrib import admin
from django.utils import timezone

from .models import DeadLetterTask


@admin.register(DeadLetterTask)
class DeadLetterTaskAdmin(admin.ModelAdmin):
    list_display = ("created_at", "task_name", "exception_type", "org_id", "resolved")
    list_filter = ("task_name", "resolved", "exception_type")
    search_fields = ("task_id", "org_id", "exception_message")
    readonly_fields = (
        "id", "task_id", "task_name", "args", "kwargs",
        "exception_type", "exception_message", "traceback",
        "org_id", "created_at",
    )
    actions = ["mark_resolved", "retry_tasks"]

    def mark_resolved(self, request, queryset):
        queryset.update(resolved=True, resolved_at=timezone.now())
    mark_resolved.short_description = "Mark selected as resolved"

    def retry_tasks(self, request, queryset):
        """Re-enqueue selected tasks. Marks each row resolved on enqueue."""
        from celery import current_app

        replayed = 0
        for row in queryset.filter(resolved=False):
            try:
                current_app.send_task(row.task_name, args=row.args, kwargs=row.kwargs)
                row.resolved = True
                row.resolved_at = timezone.now()
                row.save(update_fields=["resolved", "resolved_at"])
                replayed += 1
            except Exception as exc:
                self.message_user(request, f"Replay failed for {row.task_id}: {exc}", level="ERROR")
        self.message_user(request, f"Replayed {replayed} task(s).")
    retry_tasks.short_description = "Re-enqueue selected tasks"
