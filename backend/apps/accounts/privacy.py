"""GDPR data-subject rights: data export (Art. 15 / 20) and erasure (Art. 17).

Export bundles everything the requesting user can already read through the
API into a zip: a machine-readable ``data.json`` plus the original uploaded
files. Derived data (chunk embeddings, generation telemetry) is excluded.

Erasure has two scopes:

* **user** — the org has other members. Only the user row is deleted; content
  they created belongs to the org and keeps a NULL author (``SET_NULL`` FKs).
  If they were the last admin, the earliest-joined remaining member is
  promoted so the org is never left without an admin.
* **organization** — the user is the org's only member. The Stripe customer
  is deleted first (which cancels any subscription), then the org row, which
  cascades to every org-scoped table. Stored files are purged after commit.
"""

import json
import logging
import shutil
import tempfile
import zipfile
from pathlib import PurePosixPath

import stripe
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone

from .models import Organization, User

logger = logging.getLogger(__name__)

EXPORT_FORMAT_VERSION = 1
# Spill the in-progress zip to disk once it passes this size.
_EXPORT_SPOOL_BYTES = 10 * 1024 * 1024


class ErasureBlocked(Exception):
    """The account cannot be erased (e.g. the shared demo account)."""


class ErasureFailed(Exception):
    """An external system could not be cleaned up; nothing was deleted."""


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def _add_file(zf, field_file, arc_dir, record_id):
    """Copy a stored file into the archive. Returns its archive path, or None."""
    if not field_file:
        return None
    arcname = f"{arc_dir}/{record_id}_{PurePosixPath(field_file.name).name}"
    try:
        with field_file.open("rb") as src, zf.open(arcname, "w") as dest:
            shutil.copyfileobj(src, dest)
    except (FileNotFoundError, OSError):
        logger.warning("Export: stored file missing for %s %s", arc_dir, record_id)
        return None
    return arcname


def build_export_payload(user, zf=None):
    """Return the export dict for `user`. When `zf` is given, original files
    are written into it and referenced by archive path."""
    from apps.documents.models import Document
    from apps.proposals.models import RFP, Proposal, Template

    org = user.org
    payload = {
        "export_format_version": EXPORT_FORMAT_VERSION,
        "generated_at": timezone.now(),
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at,
            "terms_accepted_at": user.terms_accepted_at,
            "password_changed_at": user.password_changed_at,
            "google_sign_in": bool(user.google_id),
            "avatar_url": user.avatar_url,
        },
        "organization": None,
        "members": [],
        "documents": [],
        "rfps": [],
        "proposals": [],
        "templates": [],
    }
    if org is None:
        return payload

    payload["organization"] = {
        "id": org.id,
        "name": org.name,
        "subscription_tier": org.subscription_tier,
        "billing_cadence": org.billing_cadence,
        "subscription_status": org.subscription_status,
        "current_period_end": org.current_period_end,
        "created_at": org.created_at,
    }
    payload["members"] = list(
        User.objects.filter(org=org).order_by("created_at").values("email", "role", "created_at")
    )

    for doc in Document.objects.filter(org=org).select_related("uploaded_by"):
        payload["documents"].append(
            {
                "id": doc.id,
                "title": doc.title,
                "category": doc.category,
                "file_type": doc.file_type,
                "status": doc.status,
                "chunk_count": doc.chunk_count,
                "uploaded_by": doc.uploaded_by.email if doc.uploaded_by else None,
                "created_at": doc.created_at,
                "file": _add_file(zf, doc.file, "files/documents", doc.id) if zf else None,
            }
        )

    for rfp in RFP.objects.filter(org=org).select_related("created_by"):
        payload["rfps"].append(
            {
                "id": rfp.id,
                "title": rfp.title,
                "raw_text": rfp.raw_text,
                "sections": rfp.sections,
                "created_by": rfp.created_by.email if rfp.created_by else None,
                "created_at": rfp.created_at,
                "file": _add_file(zf, rfp.file, "files/rfps", rfp.id) if zf else None,
            }
        )

    payload["proposals"] = list(
        Proposal.objects.filter(org=org).values(
            "id",
            "rfp_id",
            "status",
            "tone",
            "length",
            "sections",
            "section_labels",
            "created_at",
            "updated_at",
        )
    )
    payload["templates"] = list(
        Template.objects.filter(org=org).values(
            "id", "title", "snippet", "category", "sections", "created_at", "updated_at"
        )
    )
    return payload


def build_export_archive(user):
    """Build the export zip for `user`. Returns a file object positioned at 0."""
    buffer = tempfile.SpooledTemporaryFile(max_size=_EXPORT_SPOOL_BYTES)
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        payload = build_export_payload(user, zf)
        zf.writestr("data.json", json.dumps(payload, cls=DjangoJSONEncoder, indent=2))
        zf.writestr(
            "README.txt",
            "Draftly data export\n\n"
            "data.json  - your account, organization, documents, RFPs, proposals and templates\n"
            "files/     - original files uploaded to your organization\n\n"
            "Derived data (search embeddings, generation telemetry) is not included.\n",
        )
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# Erasure
# ---------------------------------------------------------------------------


def _org_file_names(org):
    from apps.documents.models import Document
    from apps.proposals.models import RFP

    names = list(Document.objects.filter(org=org).exclude(file="").values_list("file", flat=True))
    names += list(
        RFP.objects.filter(org=org)
        .exclude(file__isnull=True)
        .exclude(file="")
        .values_list("file", flat=True)
    )
    return names


def _delete_stripe_customer(org):
    """Delete the org's Stripe customer, which also cancels its subscriptions.

    Runs before any DB deletion so a Stripe outage can never leave a deleted
    org still being billed.
    """
    if not org.stripe_customer_id or not settings.STRIPE_SECRET_KEY:
        return
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        stripe.Customer.delete(org.stripe_customer_id)
    except stripe.InvalidRequestError as exc:
        if getattr(exc, "code", None) != "resource_missing":
            raise ErasureFailed("Could not cancel your subscription. Please try again.") from exc
    except stripe.StripeError as exc:
        raise ErasureFailed("Could not cancel your subscription. Please try again.") from exc


def _schedule_file_purge(names):
    if not names:
        return

    def _enqueue():
        from .tasks import purge_storage_files

        try:
            purge_storage_files.delay(names)
        except Exception:
            # Broker unavailable — purge inline rather than leaving orphaned files.
            logger.exception("Could not enqueue file purge; purging inline")
            try:
                purge_storage_files(names)
            except Exception:
                logger.exception("Inline file purge failed for %d files", len(names))

    transaction.on_commit(_enqueue)


def erase_account(user):
    """Erase `user` per the module docstring. Returns "user" or "organization"."""
    org = user.org
    if org is not None and org.subscription_tier == Organization.Tier.DEMO:
        raise ErasureBlocked("The shared demo account cannot be deleted.")

    if org is None:
        user.delete()
        return "user"

    others = User.objects.filter(org=org).exclude(pk=user.pk).order_by("created_at")
    if others.exists():
        with transaction.atomic():
            if user.role == User.Role.ADMIN and not others.filter(role=User.Role.ADMIN).exists():
                successor = others.first()
                successor.role = User.Role.ADMIN
                successor.save(update_fields=["role"])
                logger.info("Erasure: promoted user %s to admin of org %s", successor.pk, org.pk)
            user.delete()
        logger.info("Erasure: deleted user %s from org %s", user.pk, org.pk)
        return "user"

    _delete_stripe_customer(org)
    file_names = _org_file_names(org)
    org_id = org.pk
    with transaction.atomic():
        org.delete()  # cascades to users, documents, chunks, RFPs, proposals, ...
        _schedule_file_purge(file_names)
    logger.info("Erasure: deleted org %s and %d stored files", org_id, len(file_names))
    return "organization"
