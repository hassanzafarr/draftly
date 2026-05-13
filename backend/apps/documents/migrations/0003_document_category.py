from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0002_chunk_embedding_768"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="category",
            field=models.CharField(
                choices=[
                    ("company_profile", "Company Profile"),
                    ("past_proposals", "Past Proposals"),
                    ("case_studies", "Case Studies"),
                ],
                default="company_profile",
                max_length=32,
            ),
        ),
    ]
