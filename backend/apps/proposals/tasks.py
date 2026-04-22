import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def generate_proposal_task(self, proposal_id: str):
    from .models import Proposal
    from .generator import generate_proposal_sync

    try:
        proposal = Proposal.objects.select_related("rfp", "org").get(id=proposal_id)
        sections = generate_proposal_sync(proposal.rfp.raw_text, str(proposal.org_id))
        proposal.sections = sections
        proposal.status = Proposal.Status.DRAFT
        proposal.save(update_fields=["sections", "status"])
        logger.info("Generated proposal %s", proposal_id)

    except Exception as exc:
        logger.error("Failed to generate proposal %s: %s", proposal_id, exc)
        try:
            proposal = Proposal.objects.get(id=proposal_id)
            proposal.status = Proposal.Status.FAILED
            proposal.error_message = str(exc)
            proposal.save(update_fields=["status", "error_message"])
        except Proposal.DoesNotExist:
            pass
        raise self.retry(exc=exc, countdown=30)
