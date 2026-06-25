"""Seed the six built-in (org=None) proposal templates."""

from django.db import migrations

from apps.proposals.builtin_templates import BUILTIN_TEMPLATES, seed_builtin_templates


def seed_templates(apps, schema_editor):
    Template = apps.get_model("proposals", "Template")
    seed_builtin_templates(Template)


def unseed_templates(apps, schema_editor):
    Template = apps.get_model("proposals", "Template")
    Template.objects.filter(
        org__isnull=True, title__in=[t["title"] for t in BUILTIN_TEMPLATES]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("proposals", "0010_template"),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
