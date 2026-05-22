import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DeadLetterTask",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("task_id", models.CharField(max_length=128, db_index=True)),
                ("task_name", models.CharField(max_length=255, db_index=True)),
                ("args", models.JSONField(default=list, blank=True)),
                ("kwargs", models.JSONField(default=dict, blank=True)),
                ("exception_type", models.CharField(max_length=255)),
                ("exception_message", models.TextField()),
                ("traceback", models.TextField(blank=True, default="")),
                ("org_id", models.CharField(max_length=64, blank=True, default="", db_index=True)),
                ("resolved", models.BooleanField(default=False, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("resolved_at", models.DateTimeField(null=True, blank=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["task_name", "resolved"], name="core_deadle_task_na_fd623d_idx"),
                ],
            },
        ),
    ]
