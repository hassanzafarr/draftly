import datetime as dt
from datetime import datetime, timedelta
from django.conf import settings
from django.db.models import Avg, Count, Q, Sum, F
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.core.permissions import IsOrgMember, OrgProposalQuotaPermission
from .models import RFP, Proposal, GenerationEvent
from .serializers import (
    RFPSerializer, RFPCreateSerializer,
    ProposalSerializer, ProposalUpdateSerializer,
)
from .tasks import generate_proposal_task
from .validators import classify_rfp_intent


@api_view(["GET", "POST"])
@permission_classes([IsOrgMember])
def rfp_list(request):
    if request.method == "GET":
        rfps = RFP.objects.filter(org=request.user.org)
        return Response(RFPSerializer(rfps, many=True).data)

    serializer = RFPCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

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
def generate_proposal(request, rfp_pk):
    try:
        rfp = RFP.objects.get(pk=rfp_pk, org=request.user.org)
    except RFP.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    # Semantic intent check — reject non-RFP content before consuming quota
    intent = classify_rfp_intent(rfp.raw_text)
    min_conf = getattr(settings, "RFP_INTENT_MIN_CONFIDENCE", 0.7)
    if not intent["is_rfp"] and intent["confidence"] >= min_conf:
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

    org = request.user.org
    now = dt.datetime.now(dt.timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_count = Proposal.objects.filter(org=org, created_at__gte=month_start).count()
    using_credit = monthly_count >= org.proposal_quota

    proposal = Proposal.objects.create(
        rfp=rfp,
        org=org,
        tone=tone,
        length=length,
        status=Proposal.Status.GENERATING,
    )
    generate_proposal_task.delay(str(proposal.id), using_credit=using_credit)
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
            "requirements_coverage": round((stats.get("avg_requirements_hit") or 0) / req_tot, 3) if req_tot else 0,
            "red_flags_coverage": round((stats.get("avg_red_flags_hit") or 0) / rf_tot, 3) if rf_tot else 0,
        }

    provider_breakdown = list(
        successful.values("provider").annotate(count=Count("id")).order_by("-count")
    )

    return Response({
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
                "id", "created_at", "provider", "rerank_used",
                "requirements_hit", "requirements_total",
                "red_flags_hit", "red_flags_total",
                "total_latency_ms", "success",
            )[:20]
        ),
    })


@api_view(["GET"])
@permission_classes([IsOrgMember])
def proposal_export_docx(request, pk):
    """Export a proposal as a DOCX file."""
    try:
        proposal = Proposal.objects.select_related("rfp", "org").get(
            pk=pk, org=request.user.org,
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
        events.values("provider")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Proposals by tone
    by_tone = list(
        proposals.exclude(status=Proposal.Status.FAILED)
        .values("tone")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return Response({
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
    })
