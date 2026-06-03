import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("rfp_generator")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # Prune Stripe idempotency rows older than 30 days; runs daily at 03:00 UTC.
    "prune-stripe-events-daily": {
        "task": "apps.billing.tasks.prune_stripe_events",
        "schedule": crontab(hour=3, minute=0),
    },
}
