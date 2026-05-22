"""Pricing model v1: 4 tiers (free/solo/studio/agency), seat limits, pack balance, annual billing.

Drops old starter/growth SKUs. Existing orgs on those tiers get flipped to agency
to preserve their working state (per migration strategy in docs/pricing-model.md).
"""
from django.db import migrations, models


def flip_legacy_tiers_to_agency(apps, schema_editor):
    Organization = apps.get_model("accounts", "Organization")
    Organization.objects.filter(subscription_tier__in=["starter", "growth"]).update(
        subscription_tier="agency"
    )


def reverse_flip(apps, schema_editor):
    # No reverse — legacy tiers are gone; agency is the safe landing state.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="billing_cadence",
            field=models.CharField(
                choices=[("monthly", "Monthly"), ("annual", "Annual")],
                default="monthly",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="proposal_pack_balance",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(flip_legacy_tiers_to_agency, reverse_flip),
        migrations.AlterField(
            model_name="organization",
            name="subscription_tier",
            field=models.CharField(
                choices=[
                    ("free", "Free"),
                    ("solo", "Solo"),
                    ("studio", "Studio"),
                    ("agency", "Agency"),
                ],
                default="free",
                max_length=20,
            ),
        ),
    ]
