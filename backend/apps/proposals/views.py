import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response

from apps.core.permissions import IsOrgMember, OrgProposalQuotaPermission
from apps.core.sse import sse_response, stream_changes
from apps.core.throttling import ProposalGenerateThrottle

from .models import RFP, GenerationEvent, Proposal, Template
from .serializers import (
    ProposalSerializer,
    ProposalUpdateSerializer,
    RFPCreateSerializer,
    RFPSerializer,
    TemplateSerializer,
)
from .tasks import generate_proposal_task
from .validators import classify_rfp_intent

logger = logging.getLogger(__name__)


@api_view(["GET", "POST"])
@permission_classes([IsOrgMember])
def rfp_list(request):
    if request.method == "GET":
        rfps = RFP.objects.filter(org=request.user.org)
        return Response(RFPSerializer(rfps, many=True).data)

    serializer = RFPCreateSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(
            "RFP creation validation failed | user=%s org=%s errors=%s",
            request.user.email,
            getattr(request.user.org, "id", None),
            serializer.errors,
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    resolved_text = serializer.validated_data["resolved_text"]
    file = serializer.validated_data.get("file")

    rfp = RFP.objects.create(
        org=request.user.org,
        created_by=request.user,
        title=serializer.validated_data["title"],
        raw_text=resolved_text,
        file=file,
        sections=serializer.validated_data.get("sections", []) or [],
    )
    logger.info(
        "RFP created | rfp=%s user=%s org=%s title=%r chars=%d",
        rfp.id,
        request.user.email,
        request.user.org_id,
        rfp.title,
        len(resolved_text),
    )
    return Response(RFPSerializer(rfp).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsOrgMember])
def rfp_detail(request, pk):
    try:
        rfp = RFP.objects.get(pk=pk, org=request.user.org)
    except RFP.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(RFPSerializer(rfp).data)


@api_view(["POST"])
@permission_classes([IsOrgMember, OrgProposalQuotaPermission])
@throttle_classes([ProposalGenerateThrottle])
def generate_proposal(request, rfp_pk):
    try:
        rfp = RFP.objects.get(pk=rfp_pk, org=request.user.org)
    except RFP.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    # Length ceiling — re-checked here (not only at RFP creation) so RFPs created
    # before the guard existed, or after RFP_MAX_CHARS was lowered, can't blow the
    # LLM context window and burn quota on a doomed generation.
    char_count = len(rfp.raw_text or "")
    if char_count > settings.RFP_MAX_CHARS:
        return Response(
            {
                "detail": (
                    f"RFP is too large to generate from ({char_count:,} characters; "
                    f"max {settings.RFP_MAX_CHARS:,}). Trim the RFP to its core scope "
                    "and requirements, then try again."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Semantic intent check — reject non-RFP content before consuming quota
    intent = classify_rfp_intent(rfp.raw_text)
    min_conf = getattr(settings, "RFP_INTENT_MIN_CONFIDENCE", 0.7)
    if not intent["is_rfp"] and intent["confidence"] >= min_conf:
        logger.warning(
            "RFP generation blocked by intent check | rfp=%s user=%s confidence=%.2f reason=%s",
            rfp_pk,
            request.user.email,
            intent["confidence"],
            intent["reason"],
        )
        return Response(
            {"detail": f"Input does not look like a valid RFP: {intent['reason']}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    tone = request.data.get("tone", Proposal.Tone.PROFESSIONAL)
    if tone not in Proposal.Tone.values:
        tone = Proposal.Tone.PROFESSIONAL

    length = request.data.get("length", Proposal.Length.STANDARD)
    if length not in Proposal.Length.values:
        length = Proposal.Length.STANDARD

    proposal = Proposal.objects.create(
        rfp=rfp,
        org=request.user.org,
        tone=tone,
        length=length,
        status=Proposal.Status.GENERATING,
    )
    try:
        generate_proposal_task.delay(str(proposal.id))
    except Exception as broker_exc:
        # Celery broker (Redis) is unreachable — mark the proposal as failed
        # and return a JSON 503 so the frontend can display a readable message.
        logger.error(
            "Failed to enqueue proposal task — broker unavailable | proposal=%s rfp=%s user=%s error=%s",
            proposal.id,
            rfp_pk,
            request.user.email,
            broker_exc,
        )
        proposal.status = Proposal.Status.FAILED
        proposal.status_stage = "failed"
        proposal.error_message = f"Task queue unavailable: {broker_exc}"
        proposal.save(update_fields=["status", "status_stage", "error_message"])
        return Response(
            {
                "detail": "Proposal generation service is temporarily unavailable. Please try again in a moment."
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    logger.info(
        "Proposal generation queued | proposal=%s rfp=%s user=%s org=%s tone=%s length=%s",
        proposal.id,
        rfp_pk,
        request.user.email,
        request.user.org_id,
        tone,
        length,
    )
    return Response(ProposalSerializer(proposal).data, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@permission_classes([IsOrgMember])
def proposal_list(request):
    proposals = Proposal.objects.filter(org=request.user.org).select_related("rfp")
    return Response(ProposalSerializer(proposals, many=True).data)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsOrgMember])
def proposal_detail(request, pk):
    try:
        proposal = Proposal.objects.get(pk=pk, org=request.user.org)
    except Proposal.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(ProposalSerializer(proposal).data)

    if request.method == "DELETE":
        proposal.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ProposalUpdateSerializer(proposal, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(ProposalSerializer(proposal).data)


@api_view(["GET"])
@permission_classes([IsOrgMember])
def proposal_events(request, pk):
    """SSE stream of generation status for one proposal.

    Emits `event: status` with {status, status_stage, stage_meta, error_message}
    on every change, then `event: done` once the proposal leaves `generating`.
    Sections are intentionally excluded — the client fetches the full proposal
    once on `done` instead of shipping the whole draft on every stage change.
    """
    if not Proposal.objects.filter(pk=pk, org=request.user.org).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    def fetch_state():
        return (
            Proposal.objects.filter(pk=pk)
            .values("status", "status_stage", "stage_meta", "error_message")
            .first()
        )

    return sse_response(
        stream_changes(
            fetch_state,
            is_terminal=lambda state: state["status"] != Proposal.Status.GENERATING,
        )
    )


@api_view(["GET", "POST"])
@permission_classes([IsOrgMember])
def template_list(request):
    """List built-in + org templates, or create an org template."""
    if request.method == "GET":
        templates = Template.objects.filter(is_active=True).filter(
            Q(org__isnull=True) | Q(org=request.user.org)
        )
        return Response(TemplateSerializer(templates, many=True).data)

    serializer = TemplateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    template = serializer.save(org=request.user.org, created_by=request.user)
    return Response(TemplateSerializer(template).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsOrgMember])
def template_detail(request, pk):
    try:
        template = Template.objects.filter(Q(org__isnull=True) | Q(org=request.user.org)).get(
            pk=pk, is_active=True
        )
    except Template.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(TemplateSerializer(template).data)

    if template.is_builtin:
        return Response(
            {"detail": "Built-in templates cannot be modified."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "DELETE":
        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = TemplateSerializer(template, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(TemplateSerializer(template).data)


@api_view(["GET"])
@permission_classes([IsOrgMember])
def generation_metrics(request):
    """Aggregate retrieval + generation telemetry for current org."""
    events = GenerationEvent.objects.filter(org=request.user.org)
    total = events.count()
    if total == 0:
        return Response({"total": 0})

    successful = events.filter(success=True)
    reranked = successful.filter(rerank_used=True)
    vector_only = successful.filter(rerank_used=False)

    def _avgs(qs):
        return qs.aggregate(
            count=Count("id"),
            avg_total_ms=Avg("total_latency_ms"),
            avg_rerank_ms=Avg("rerank_latency_ms"),
            avg_generation_ms=Avg("generation_latency_ms"),
            avg_requirements_hit=Avg("requirements_hit"),
            avg_requirements_total=Avg("requirements_total"),
            avg_red_flags_hit=Avg("red_flags_hit"),
            avg_red_flags_total=Avg("red_flags_total"),
        )

    def _coverage(stats):
        req_tot = stats.get("avg_requirements_total") or 0
        rf_tot = stats.get("avg_red_flags_total") or 0
        return {
            **stats,
            "requirements_coverage": round((stats.get("avg_requirements_hit") or 0) / req_tot, 3)
            if req_tot
            else 0,
            "red_flags_coverage": round((stats.get("avg_red_flags_hit") or 0) / rf_tot, 3)
            if rf_tot
            else 0,
        }

    provider_breakdown = list(
        successful.values("provider").annotate(count=Count("id")).order_by("-count")
    )

    return Response(
        {
            "total": total,
            "success_rate": round(successful.count() / total, 3),
            "rerank_adoption": round(reranked.count() / total, 3),
            "tokens_saved_estimate_chunks": (events.aggregate(s=Sum("fetch_top_k"))["s"] or 0)
            - (events.aggregate(s=Sum("rerank_top_k"))["s"] or 0),
            "with_rerank": _coverage(_avgs(reranked)),
            "without_rerank": _coverage(_avgs(vector_only)),
            "providers": provider_breakdown,
            "recent": list(
                events.order_by("-created_at").values(
                    "id",
                    "created_at",
                    "provider",
                    "rerank_used",
                    "requirements_hit",
                    "requirements_total",
                    "red_flags_hit",
                    "red_flags_total",
                    "total_latency_ms",
                    "success",
                )[:20]
            ),
        }
    )


@api_view(["GET"])
@permission_classes([IsOrgMember])
def proposal_export_docx(request, pk):
    """Export a proposal as a DOCX file."""
    try:
        proposal = Proposal.objects.select_related("rfp", "org").get(
            pk=pk,
            org=request.user.org,
        )
    except Proposal.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    from .export import generate_docx

    buffer = generate_docx(proposal)

    safe_title = (proposal.rfp.title or "proposal").replace(" ", "_")[:60]
    filename = f"{safe_title}.docx"

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["GET"])
@permission_classes([IsOrgMember])
def analytics_stats(request):
    """Real analytics data for the frontend Analytics page."""
    org = request.user.org
    proposals = Proposal.objects.filter(org=org)
    total = proposals.count()
    final_count = proposals.filter(status=Proposal.Status.FINAL).count()
    draft_count = proposals.filter(status=Proposal.Status.DRAFT).count()
    generating_count = proposals.filter(status=Proposal.Status.GENERATING).count()
    failed_count = proposals.filter(status=Proposal.Status.FAILED).count()

    # Success rate = finalized / (finalized + draft) — exclude generating/failed
    completed = final_count + draft_count
    success_rate = round((final_count / completed * 100) if completed else 0, 1)

    # Average generation time
    events = GenerationEvent.objects.filter(org=org, success=True)
    avg_latency = events.aggregate(avg=Avg("total_latency_ms"))["avg"] or 0
    avg_response_seconds = round(avg_latency / 1000, 1)

    # Monthly performance (last 12 months)
    twelve_months_ago = datetime.now() - timedelta(days=365)
    monthly_raw = (
        proposals.filter(created_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            drafted=Count("id"),
            finalized=Count("id", filter=Q(status=Proposal.Status.FINAL)),
        )
        .order_by("month")
    )
    monthly_performance = [
        {
            "month": row["month"].strftime("%b"),
            "drafted": row["drafted"],
            "won": row["finalized"],
        }
        for row in monthly_raw
    ]

    # Provider breakdown
    provider_breakdown = list(
        events.values("provider").annotate(count=Count("id")).order_by("-count")
    )

    # Proposals by tone
    by_tone = list(
        proposals.exclude(status=Proposal.Status.FAILED)
        .values("tone")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return Response(
        {
            "total_proposals": total,
            "success_rate": success_rate,
            "avg_response_seconds": avg_response_seconds,
            "final_count": final_count,
            "draft_count": draft_count,
            "generating_count": generating_count,
            "failed_count": failed_count,
            "monthly_performance": monthly_performance,
            "providers": provider_breakdown,
            "by_tone": by_tone,
        }
    )
