from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from apps.core.permissions import IsOrgMember, OrgDocQuotaPermission
from .models import Document
from .serializers import DocumentSerializer, DocumentUploadSerializer
from .tasks import ingest_document


@api_view(["GET", "POST"])
@permission_classes([IsOrgMember, OrgDocQuotaPermission])
def document_list(request):
    if request.method == "GET":
        docs = Document.objects.filter(org=request.user.org)
        return Response(DocumentSerializer(docs, many=True).data)

    parser_classes_list = [MultiPartParser]
    serializer = DocumentUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    file = serializer.validated_data["file"]
    ext = file.name.rsplit(".", 1)[-1].lower()
    title = serializer.validated_data.get("title") or file.name

    doc = Document.objects.create(
        org=request.user.org,
        uploaded_by=request.user,
        title=title,
        file=file,
        file_type=ext,
    )
    ingest_document.delay(str(doc.id))
    return Response(DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "DELETE"])
@permission_classes([IsOrgMember])
def document_detail(request, pk):
    try:
        doc = Document.objects.get(pk=pk, org=request.user.org)
    except Document.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(DocumentSerializer(doc).data)

    doc.chunks.all().delete()
    doc.file.delete(save=False)
    doc.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
