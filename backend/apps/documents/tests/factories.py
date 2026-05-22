import factory
from django.core.files.base import ContentFile
from factory.django import DjangoModelFactory

from apps.accounts.tests.factories import OrganizationFactory, UserFactory
from apps.documents.models import Document


class DocumentFactory(DjangoModelFactory):
    """Create a Document row without triggering Celery ingestion.

    The file is an in-memory ContentFile so no real disk I/O happens beyond
    what Django's FileField requires for storage write.
    """

    class Meta:
        model = Document

    org = factory.SubFactory(OrganizationFactory)
    uploaded_by = factory.SubFactory(UserFactory, org=factory.SelfAttribute("..org"))
    title = factory.Sequence(lambda n: f"Document {n}")
    file_type = Document.FileType.TXT
    category = Document.Category.COMPANY_PROFILE
    status = Document.Status.PROCESSED
    chunk_count = 0

    file = factory.LazyAttribute(
        lambda obj: ContentFile(b"test content", name=f"{obj.title}.txt")
    )
