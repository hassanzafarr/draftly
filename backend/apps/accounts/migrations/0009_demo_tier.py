from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_invitation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="subscription_tier",
            field=models.CharField(
                choices=[
                    ("free", "Free"),
                    ("solo", "Solo"),
                    ("studio", "Studio"),
                    ("agency", "Agency"),
                    ("demo", "Demo"),
                ],
                default="free",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="demo_reset_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
