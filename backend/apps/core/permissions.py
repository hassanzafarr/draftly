import calendar
import datetime

from rest_framework.permissions import BasePermission

from apps.documents.models import Document
from apps.proposals.models import Proposal


def _billing_period_start(period_end, cadence):
    """Return the start of the billing period given its end date and cadence."""
    if cadence == "annual":
        try:
            return period_end.replace(year=period_end.year - 1)
        except ValueError:
            return period_end.replace(year=period_end.year - 1, day=28)
    # monthly
    if period_end.month == 1:
        year, month = period_end.year - 1, 12
    else:
        year, month = period_end.year, period_end.month - 1
    max_day = calendar.monthrange(year, month)[1]
    return period_end.replace(year=year, month=month, day=min(period_end.day, max_day))


class IsOrgMember(BasePermission):
    """Allow only authenticated users with an org."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.org)


class IsOrgAdmin(BasePermission):
    """Allow only authenticated org members with the admin role."""

    message = "Only organization admins can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.org
            and request.user.role == "admin"
        )


class OrgDocQuotaPermission(BasePermission):
    """Block document upload if org is at its doc quota."""

    message = "Document quota reached for your subscription tier."

    def has_permission(self, request, view):
        if request.method != "POST":
            return True
        org = request.user.org
        current = Document.objects.filter(org=org, status="processed").count()
        return current < org.doc_quota


class OrgProposalQuotaPermission(BasePermission):
    """Block proposal generation if org is at its monthly quota."""

    message = "Monthly proposal quota reached. Upgrade your plan to continue."

    def has_permission(self, request, view):
        if request.method != "POST":
            return True
        org = request.user.org
        now = datetime.datetime.now(datetime.UTC)
        # Paid subscribers: align quota window to Stripe billing period so
        # annual subscribers don't reset every UTC 1st of the calendar month.
        if org.subscription_tier != "free" and org.current_period_end:
            period_start = _billing_period_start(org.current_period_end, org.billing_cadence)
        else:
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current = Proposal.objects.filter(org=org, created_at__gte=period_start).count()
        return current < org.proposal_quota
