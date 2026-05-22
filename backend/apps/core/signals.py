"""Celery signal handlers — Sentry tagging + dead-letter persistence.

`task_failure` fires AFTER all retries are exhausted, so any row we write
here represents a terminal failure that an operator must address.
"""
import logging
import traceback as _tb_mod
from typing import Any

from celery.signals import task_failure

logger = logging.getLogger(__name__)


# Tasks we want to tag with extra org-scoped context for Sentry routing.
# Maps (task_name -> arg_index_of_resource_id) for resolving the org id.
_RESOURCE_TASKS = {
    "apps.documents.tasks.ingest_document": ("document", 0),
    "apps.proposals.tasks.generate_proposal_task": ("proposal", 0),
}


def _resolve_org_id(task_name: str, args: tuple, kwargs: dict) -> str:
    """Best-effort lookup of org_id for the failing task's resource.

    Failures here are swallowed — we do not want signal handling to itself
    explode and lose the original failure.
    """
    spec = _RESOURCE_TASKS.get(task_name)
    if not spec:
        return ""
    resource, idx = spec
    try:
        resource_id = args[idx] if args and len(args) > idx else kwargs.get(f"{resource}_id")
        if not resource_id:
            return ""
        if resource == "document":
            from apps.documents.models import Document
            row = Document.objects.filter(id=resource_id).only("org_id").first()
        elif resource == "proposal":
            from apps.proposals.models import Proposal
            row = Proposal.objects.filter(id=resource_id).only("org_id").first()
        else:
            return ""
        return str(row.org_id) if row else ""
    except Exception:
        return ""


def _to_sentry(task_name: str, task_id: str, org_id: str, exc: BaseException) -> None:
    """Capture to Sentry with structured tags so alert rules can route by task."""
    try:
        import sentry_sdk
    except ImportError:
        return

    with sentry_sdk.push_scope() as scope:
        scope.set_tag("celery.task_name", task_name)
        scope.set_tag("celery.task_id", task_id)
        scope.set_tag("celery.terminal_failure", "true")
        if org_id:
            scope.set_tag("org_id", org_id)
        scope.fingerprint = ["celery-dlq", task_name, type(exc).__name__]
        sentry_sdk.capture_exception(exc)


@task_failure.connect
def on_task_failure(
    sender: Any = None,
    task_id: str = "",
    exception: BaseException = None,
    args: tuple = (),
    kwargs: dict = None,
    traceback: Any = None,
    einfo: Any = None,
    **_,
):
    """Persist a DLQ row + push tagged event to Sentry."""
    kwargs = kwargs or {}
    task_name = getattr(sender, "name", "") or ""

    org_id = _resolve_org_id(task_name, args or (), kwargs)
    exc = exception or (einfo.exception if einfo else None)
    if exc is None:
        return

    _to_sentry(task_name, task_id, org_id, exc)

    # Persist DLQ row — wrapped so a DB hiccup never re-raises into the worker.
    try:
        from .models import DeadLetterTask

        tb_text = ""
        if traceback is not None:
            try:
                tb_text = "".join(_tb_mod.format_tb(traceback))
            except Exception:
                tb_text = ""
        if not tb_text and einfo is not None:
            tb_text = str(getattr(einfo, "traceback", "") or "")

        DeadLetterTask.objects.create(
            task_id=task_id or "",
            task_name=task_name,
            args=list(args or []),
            kwargs=dict(kwargs),
            exception_type=type(exc).__name__,
            exception_message=str(exc)[:4000],
            traceback=tb_text[:8000],
            org_id=org_id,
        )
    except Exception as persist_exc:
        logger.error("DLQ persist failed for %s/%s: %s", task_name, task_id, persist_exc)
