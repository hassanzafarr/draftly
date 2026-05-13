import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("proposals", "0002_add_tone_to_proposal"),
    ]

    operations = [
        migrations.CreateModel(
            name="GenerationEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("fetch_top_k", models.IntegerField(default=0)),
                ("rerank_top_k", models.IntegerField(default=0)),
                ("rerank_used", models.BooleanField(default=False)),
                ("rerank_latency_ms", models.IntegerField(default=0)),
                ("retrieval_latency_ms", models.IntegerField(default=0)),
                ("chunks_used", models.JSONField(default=list)),
                ("provider", models.CharField(blank=True, max_length=20)),
                ("generation_latency_ms", models.IntegerField(default=0)),
                ("total_latency_ms", models.IntegerField(default=0)),
                ("rfp_brief", models.JSONField(default=dict)),
                ("requirements_total", models.IntegerField(default=0)),
                ("requirements_hit", models.IntegerField(default=0)),
                ("red_flags_total", models.IntegerField(default=0)),
                ("red_flags_hit", models.IntegerField(default=0)),
                ("section_word_counts", models.JSONField(default=dict)),
                ("success", models.BooleanField(default=False)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("org", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="generation_events", to="accounts.organization")),
                ("proposal", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="event", to="proposals.proposal")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["org", "-created_at"], name="proposals_g_org_id_created_idx")],
            },
        ),
    ]
