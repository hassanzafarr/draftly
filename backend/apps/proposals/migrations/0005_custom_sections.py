from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0004_proposal_status_stage"),
    ]

    operations = [
        migrations.AddField(
            model_name="rfp",
            name="sections",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="proposal",
            name="section_labels",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
