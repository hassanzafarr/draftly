from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0005_custom_sections"),
    ]

    operations = [
        migrations.AddField(
            model_name="proposal",
            name="length",
            field=models.CharField(
                choices=[
                    ("concise", "Concise"),
                    ("standard", "Standard"),
                    ("detailed", "Detailed"),
                    ("comprehensive", "Comprehensive"),
                ],
                default="standard",
                max_length=20,
            ),
        ),
    ]
