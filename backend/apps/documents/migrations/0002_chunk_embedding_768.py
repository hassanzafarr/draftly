from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE documents_chunk ALTER COLUMN embedding TYPE vector(768);",
            reverse_sql="ALTER TABLE documents_chunk ALTER COLUMN embedding TYPE vector(1536);",
        ),
    ]
