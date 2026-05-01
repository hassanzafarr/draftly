from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="proposal",
            name="tone",
            field=models.CharField(
                choices=[
                    ("professional", "Professional"),
                    ("formal", "Formal"),
                    ("persuasive", "Persuasive"),
                    ("friendly", "Friendly"),
                    ("technical", "Technical"),
                ],
                default="professional",
                max_length=20,
            ),
        ),
    ]
