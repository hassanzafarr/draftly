"""Core models — currently just the Celery dead-letter table.

DeadLetterTask records terminal Celery task failures (after all retries
exhausted) so ops can inspect and reprocess without scraping Sentry.
"""
import uuid

from django.db import models


class DeadLetterTask(models.Model):
    """One row per Celery task that exhausted retries and failed terminally.

    Populated by `apps.core.signals.on_task_failure`. Sentry receives the
    same exception via its CeleryIntegration; this table exists so operators
    can replay or audit failed tasks from Django admin without leaving the
    app.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_id = models.CharField(max_length=128, db_index=True)
    task_name = models.CharField(max_length=255, db_index=True)
    args = models.JSONField(default=list, blank=True)
    kwargs = models.JSONField(default=dict, blank=True)
    exception_type = models.CharField(max_length=255)
    exception_message = models.TextField()
    traceback = models.TextField(blank=True, default="")
    org_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    resolved = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["task_name", "resolved"]),
        ]

    def __str__(self):
        return f"DLQ {self.task_name} {self.task_id} ({self.exception_type})"
