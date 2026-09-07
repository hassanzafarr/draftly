"""Shared setup for the public demo account (login button, no signup required).

Used by both the `seed_demo` management command (initial/manual seed) and the
`demo_login` view (lazy reset when the demo org's data has gone stale).
"""

import logging
import uuid
from datetime import timedelta
from pathlib import Path

from django.core.files.base import ContentFile
from django.utils import timezone

from .models import Organization, User

logger = logging.getLogger(__name__)

# Fixed IDs so the demo org/user are singletons — re-running the seed command
# or hitting the login endpoint never creates duplicates.
DEMO_ORG_ID = uuid.UUID("00000000-0000-0000-0000-0000000000d0")
DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000d1")
DEMO_ORG_NAME = "Draftly Demo"
DEMO_EMAIL = "demo@draftly.software"

DEMO_RESET_INTERVAL = timedelta(hours=24)

DEMO_SEED_DIR = Path(__file__).parent / "demo_seed"

# (filename in demo_seed/, display title, category, file_type)
DEMO_SEED_FILES = [
    (
        "nexrai_company_profile.docx",
        "NexrAI — Company Profile",
        "company_profile",
        "docx",
    ),
    (
        "case_study_01_physio_voice_receptionist.pdf",
        "Case Study — Physio Voice Receptionist",
        "case_studies",
        "pdf",
    ),
    (
        "case_study_02_skincare_marketing_automation.pdf",
        "Case Study — Skincare Marketing Automation",
        "case_studies",
        "pdf",
    ),
    (
        "case_study_03_saas_support_agent.pdf",
        "Case Study — SaaS Support Agent",
        "case_studies",
        "pdf",
    ),
    (
        "case_study_04_customs_agentic_workflow.pdf",
        "Case Study — Customs Agentic Workflow",
        "case_studies",
        "pdf",
    ),
    (
        "past_proposal_01_dental_voice_receptionist.pdf",
        "Past Proposal — Dental Voice Receptionist",
        "past_proposals",
        "pdf",
    ),
    (
        "past_proposal_02_ecommerce_marketing_automation.pdf",
        "Past Proposal — Ecommerce Marketing Automation",
        "past_proposals",
        "pdf",
    ),
    (
        "past_proposal_03_saas_support_agent.pdf",
        "Past Proposal — SaaS Support Agent",
        "past_proposals",
        "pdf",
    ),
    (
        "past_proposal_04_logistics_quote_agent.pdf",
        "Past Proposal — Logistics Quote Agent",
        "past_proposals",
        "pdf",
    ),
]


def get_or_create_demo():
    """Return (org, user), creating them on first call. Idempotent."""
    org, _ = Organization.objects.get_or_create(
        id=DEMO_ORG_ID,
        defaults={"name": DEMO_ORG_NAME, "subscription_tier": Organization.Tier.DEMO},
    )
    if org.subscription_tier != Organization.Tier.DEMO:
        org.subscription_tier = Organization.Tier.DEMO
        org.save(update_fields=["subscription_tier"])

    user, created = User.objects.get_or_create(
        id=DEMO_USER_ID,
        defaults={
            "email": DEMO_EMAIL,
            "org": org,
            "role": User.Role.ADMIN,
            "is_active": True,
            "terms_accepted_at": timezone.now(),
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])

    return org, user


def is_demo_stale(org):
    return org.demo_reset_at is None or timezone.now() - org.demo_reset_at > DEMO_RESET_INTERVAL


def reset_demo_data(org, user):
    """Wipe the demo org's RFPs/proposals/documents and reseed the sample doc set."""
    from apps.documents.models import Document
    from apps.documents.tasks import ingest_document
    from apps.proposals.models import RFP

    RFP.objects.filter(org=org).delete()  # cascades to Proposal, GenerationEvent
    Document.objects.filter(org=org).delete()  # cascades to Chunk

    for filename, title, category, file_type in DEMO_SEED_FILES:
        data = (DEMO_SEED_DIR / filename).read_bytes()
        doc = Document(
            org=org,
            uploaded_by=user,
            title=title,
            file_type=file_type,
            category=category,
        )
        doc.file.save(filename, ContentFile(data), save=False)
        doc.save()
        try:
            ingest_document(str(doc.id))
        except Exception:
            logger.exception("Demo seed document %s failed to ingest", filename)

    org.demo_reset_at = timezone.now()
    org.save(update_fields=["demo_reset_at"])
