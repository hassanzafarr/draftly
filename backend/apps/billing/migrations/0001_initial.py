from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="StripeEvent",
            fields=[
                ("event_id", models.CharField(max_length=255, primary_key=True, serialize=False)),
                ("event_type", models.CharField(max_length=100)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "indexes": [models.Index(fields=["received_at"], name="billing_str_receive_idx")],
            },
        ),
    ]
