"""Helpers for recording terminal Celery task failures.

The `task_failure` signal in `signals.py` is the primary path — it fires for
any failing task in a real worker. Eager mode (`CELERY_TASK_ALWAYS_EAGER`)
bypasses signal dispatch, so tasks running in tests or via `.apply()` must
call `record_failure` directly from their terminal except block.
"""
import logging
import traceback as _tb_mod
from typing import Optional

logger = logging.getLogger(__name__)


def record_failure(
    *,
    task_name: str,
    task_id: str,
    args: Optional[tuple] = None,
    kwargs: Optional[dict] = None,
    exception: BaseException,
    org_id: str = "",
) -> None:
    """Persist a DLQ row and forward to Sentry with structured tags.

    Idempotent on (task_id, exception_type): if the signal handler already
    wrote a row for this task_id, we no-op rather than duplicate.
    """
    args = args or ()
    kwargs = kwargs or {}
    exc_type = type(exception).__name__

    # Sentry first — DB writes are the unreliable leg.
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            scope.set_tag("celery.task_name", task_name)
            scope.set_tag("celery.task_id", task_id)
            scope.set_tag("celery.terminal_failure", "true")
            if org_id:
                scope.set_tag("org_id", org_id)
            scope.fingerprint = ["celery-dlq", task_name, exc_type]
            sentry_sdk.capture_exception(exception)
    except ImportError:
        pass
    except Exception as sentry_exc:
        logger.warning("Sentry capture failed: %s", sentry_exc)

    try:
        from .models import DeadLetterTask

        if task_id and DeadLetterTask.objects.filter(task_id=task_id, exception_type=exc_type).exists():
            return

        tb = exception.__traceback__
        tb_text = ""
        if tb is not None:
            try:
                tb_text = "".join(_tb_mod.format_tb(tb))
            except Exception:
                tb_text = ""

        DeadLetterTask.objects.create(
            task_id=task_id or "",
            task_name=task_name,
            args=list(args),
            kwargs=dict(kwargs),
            exception_type=exc_type,
            exception_message=str(exception)[:4000],
            traceback=tb_text[:8000],
            org_id=org_id,
        )
    except Exception as persist_exc:
        logger.error("DLQ persist failed for %s/%s: %s", task_name, task_id, persist_exc)
