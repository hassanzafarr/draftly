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
    # Optional custom section labels supplied by user/template. Empty list = use default 10-section schema.
    sections = models.JSONField(default=list, blank=True)
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

    class Tone(models.TextChoices):
        PROFESSIONAL = "professional", "Professional"
        FORMAL = "formal", "Formal"
        PERSUASIVE = "persuasive", "Persuasive"
        FRIENDLY = "friendly", "Friendly"
        TECHNICAL = "technical", "Technical"

    class Length(models.TextChoices):
        CONCISE = "concise", "Concise"
        STANDARD = "standard", "Standard"
        DETAILED = "detailed", "Detailed"
        COMPREHENSIVE = "comprehensive", "Comprehensive"

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
    tone = models.CharField(max_length=20, choices=Tone.choices, default=Tone.PROFESSIONAL)
    length = models.CharField(max_length=20, choices=Length.choices, default=Length.STANDARD)
    sections = models.JSONField(default=dict)
    # When custom sections were used, this maps section key → display label.
    # Empty dict = default 10-section schema (frontend falls back to built-in labels).
    section_labels = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GENERATING)
    status_stage = models.CharField(max_length=32, default="queued", blank=True)
    stage_meta = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Proposal for {self.rfp.title}"


class GenerationEvent(models.Model):
    """Per-proposal telemetry for evaluating retrieval + generation quality."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.OneToOneField(Proposal, on_delete=models.CASCADE, related_name="event")
    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="generation_events"
    )

    # Retrieval
    fetch_top_k = models.IntegerField(default=0)
    rerank_top_k = models.IntegerField(default=0)
    rerank_used = models.BooleanField(default=False)
    rerank_latency_ms = models.IntegerField(default=0)
    retrieval_latency_ms = models.IntegerField(default=0)
    chunks_used = models.JSONField(
        default=list
    )  # [{document_id, source_title, category, rerank_score, vector_rank}]

    # Generation
    provider = models.CharField(max_length=20, blank=True)  # "gemini" | "groq"
    generation_latency_ms = models.IntegerField(default=0)
    total_latency_ms = models.IntegerField(default=0)

    # Quality signals
    rfp_brief = models.JSONField(default=dict)
    requirements_total = models.IntegerField(default=0)
    requirements_hit = models.IntegerField(default=0)
    red_flags_total = models.IntegerField(default=0)
    red_flags_hit = models.IntegerField(default=0)
    section_word_counts = models.JSONField(default=dict)  # {section_key: int}

    # Outcome
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["org", "-created_at"])]

    @property
    def requirements_coverage(self) -> float:
        if self.requirements_total == 0:
            return 0.0
        return round(self.requirements_hit / self.requirements_total, 3)

    @property
    def red_flags_coverage(self) -> float:
        if self.red_flags_total == 0:
            return 0.0
        return round(self.red_flags_hit / self.red_flags_total, 3)
