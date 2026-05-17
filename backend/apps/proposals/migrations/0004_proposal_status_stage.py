from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0003_generationevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="proposal",
            name="status_stage",
            field=models.CharField(blank=True, default="queued", max_length=32),
        ),
        migrations.AddField(
            model_name="proposal",
            name="stage_meta",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
