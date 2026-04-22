from rest_framework.permissions import BasePermission
from apps.documents.models import Document
from apps.proposals.models import Proposal
import datetime


class IsOrgMember(BasePermission):
    """Allow only authenticated users with an org."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.org)


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
    message = "Monthly proposal quota reached for your subscription tier."

    def has_permission(self, request, view):
        if request.method != "POST":
            return True
        org = request.user.org
        now = datetime.datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current = Proposal.objects.filter(org=org, created_at__gte=month_start).count()
        return current < org.proposal_quota
