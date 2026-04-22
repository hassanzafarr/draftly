import uuid
from django.db import models
from apps.accounts.models import Organization, User


class RFP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="rfps")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="rfps")
    title = models.CharField(max_length=500)
    raw_text = models.TextField()
    file = models.FileField(upload_to="rfps/%Y/%m/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Proposal(models.Model):
    class Status(models.TextChoices):
        GENERATING = "generating", "Generating"
        DRAFT = "draft", "Draft"
        FINAL = "final", "Final"
        FAILED = "failed", "Failed"

    SECTION_KEYS = [
        "executive_summary",
        "understanding_requirements",
        "proposed_solution",
        "relevant_experience",
        "team_qualifications",
        "project_timeline",
        "methodology",
        "pricing",
        "why_us",
        "appendix",
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rfp = models.ForeignKey(RFP, on_delete=models.CASCADE, related_name="proposals")
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="proposals")
    sections = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GENERATING)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Proposal for {self.rfp.title}"
