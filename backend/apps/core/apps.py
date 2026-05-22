from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        # Wire Celery task_failure → Sentry + DeadLetterTask record.
        from . import signals  # noqa: F401
