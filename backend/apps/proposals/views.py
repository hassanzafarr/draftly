from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.core.permissions import IsOrgMember, OrgProposalQuotaPermission
from .models import RFP, Proposal
from .serializers import (
    RFPSerializer, RFPCreateSerializer,
    ProposalSerializer, ProposalUpdateSerializer,
)
from .tasks import generate_proposal_task
from apps.documents.pipeline import extract_text


@api_view(["GET", "POST"])
@permission_classes([IsOrgMember])
def rfp_list(request):
    if request.method == "GET":
        rfps = RFP.objects.filter(org=request.user.org)
        return Response(RFPSerializer(rfps, many=True).data)

    serializer = RFPCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    raw_text = serializer.validated_data.get("raw_text", "").strip()
    file = serializer.validated_data.get("file")
    if file:
        ext = file.name.rsplit(".", 1)[-1].lower()
        extracted_text = extract_text(file.read(), ext).strip()
        file.seek(0)
        if raw_text:
            raw_text = f"{raw_text}\n\n--- ATTACHED RFP FILE TEXT ---\n\n{extracted_text}"
        else:
            raw_text = extracted_text

    rfp = RFP.objects.create(
        org=request.user.org,
        created_by=request.user,
        title=serializer.validated_data["title"],
        raw_text=raw_text,
        file=file,
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

    tone = request.data.get("tone", Proposal.Tone.PROFESSIONAL)
    if tone not in Proposal.Tone.values:
        tone = Proposal.Tone.PROFESSIONAL

    proposal = Proposal.objects.create(
        rfp=rfp,
        org=request.user.org,
        tone=tone,
        status=Proposal.Status.GENERATING,
    )
    generate_proposal_task.delay(str(proposal.id))
    return Response(ProposalSerializer(proposal).data, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@permission_classes([IsOrgMember])
def proposal_list(request):
    proposals = Proposal.objects.filter(org=request.user.org).select_related("rfp")
    return Response(ProposalSerializer(proposals, many=True).data)


@api_view(["GET", "PATCH"])
@permission_classes([IsOrgMember])
def proposal_detail(request, pk):
    try:
        proposal = Proposal.objects.get(pk=pk, org=request.user.org)
    except Proposal.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(ProposalSerializer(proposal).data)

    serializer = ProposalUpdateSerializer(proposal, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(ProposalSerializer(proposal).data)
