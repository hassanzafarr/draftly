"""Drop legacy credit_balance + proposal_pack_balance columns.

These were removed from the Organization model in commit fe1fe4d, but that
commit edited the prior migrations in-place rather than adding a removal
migration. Environments that ran the earlier migrations still have the
NOT NULL columns, which break new INSERTs (registration fails).

Raw SQL with IF EXISTS so it's a no-op on fresh DBs.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_billing_fields"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE accounts_organization "
                "DROP COLUMN IF EXISTS credit_balance, "
                "DROP COLUMN IF EXISTS proposal_pack_balance;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
