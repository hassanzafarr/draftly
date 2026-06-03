import logging

from celery import shared_task

logger = logging.getLogger(__name__)


def _persist_event(proposal, metrics: dict, *, success: bool, error_message: str = "") -> None:
    from .evaluator import evaluate_proposal
    from .models import GenerationEvent

    metrics = metrics or {}
    quality = {}
    if success:
        try:
            quality = evaluate_proposal(proposal.sections, metrics.get("rfp_brief") or {})
        except Exception as exc:
            logger.warning("evaluate_proposal failed for %s: %s", proposal.id, exc)

    defaults = {
        "org": proposal.org,
        "fetch_top_k": metrics.get("fetch_top_k", 0),
        "rerank_top_k": metrics.get("rerank_top_k", 0),
        "rerank_used": metrics.get("rerank_used", False),
        "rerank_latency_ms": metrics.get("rerank_latency_ms", 0),
        "retrieval_latency_ms": metrics.get("retrieval_latency_ms", 0),
        "chunks_used": metrics.get("chunks_used", []),
        "provider": metrics.get("provider", ""),
        "generation_latency_ms": metrics.get("generation_latency_ms", 0),
        "total_latency_ms": metrics.get("total_latency_ms", 0),
        "rfp_brief": metrics.get("rfp_brief", {}),
        "requirements_total": quality.get("requirements_total", 0),
        "requirements_hit": quality.get("requirements_hit", 0),
        "red_flags_total": quality.get("red_flags_total", 0),
        "red_flags_hit": quality.get("red_flags_hit", 0),
        "section_word_counts": quality.get("section_word_counts", {}),
        "success": success,
        "error_message": error_message,
    }
    GenerationEvent.objects.update_or_create(proposal=proposal, defaults=defaults)


@shared_task(bind=True, max_retries=2)
def generate_proposal_task(self, proposal_id: str):
    from .generator import generate_proposal_with_metrics
    from .models import Proposal

    metrics: dict = {}
    try:
        proposal = Proposal.objects.select_related("rfp", "org").get(id=proposal_id)

        Proposal.objects.filter(id=proposal_id).update(status_stage="analyzing", stage_meta={})

        def _on_stage(stage: str, meta: dict):
            Proposal.objects.filter(id=proposal_id).update(
                status_stage=stage, stage_meta=meta or {}
            )

        sections, metrics = generate_proposal_with_metrics(
            proposal.rfp.raw_text,
            str(proposal.org_id),
            proposal.tone,
            on_stage=_on_stage,
            custom_section_labels=proposal.rfp.sections or None,
            length=proposal.length,
        )
        proposal.sections = sections
        proposal.section_labels = metrics.get("section_labels") or {}
        proposal.status = Proposal.Status.DRAFT
        proposal.status_stage = "done"
        proposal.stage_meta = {"provider": metrics.get("provider")}
        proposal.save(
            update_fields=["sections", "section_labels", "status", "status_stage", "stage_meta"]
        )
        _persist_event(proposal, metrics, success=True)
        logger.info(
            "Generated proposal %s — provider=%s rerank=%s lat=%sms",
            proposal_id,
            metrics.get("provider"),
            metrics.get("rerank_used"),
            metrics.get("total_latency_ms"),
        )

    except Exception as exc:
        logger.error("Failed to generate proposal %s: %s", proposal_id, exc)
        org_id = ""
        try:
            proposal = Proposal.objects.get(id=proposal_id)
            org_id = str(proposal.org_id)
            proposal.status = Proposal.Status.FAILED
            proposal.status_stage = "failed"
            proposal.error_message = str(exc)
            proposal.save(update_fields=["status", "status_stage", "error_message"])
            _persist_event(proposal, metrics, success=False, error_message=str(exc))
        except Proposal.DoesNotExist:
            pass
        if "429" in str(exc) or "quota" in str(exc).lower() or "rate" in str(exc).lower():
            return
        # Final attempt? Record terminal failure for ops + Sentry.
        if self.request.retries >= self.max_retries:
            from apps.core.dlq import record_failure

            record_failure(
                task_name=self.name,
                task_id=self.request.id or "",
                args=(proposal_id,),
                exception=exc,
                org_id=org_id,
            )
            raise
        raise self.retry(exc=exc, countdown=30) from exc
