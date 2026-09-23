from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Organization
from apps.mcp_tokens.models import MCPToken


class Command(BaseCommand):
    help = "Create an MCP server bearer token for an org. The secret is printed once and cannot be recovered afterward."

    def add_arguments(self, parser):
        parser.add_argument("org_id", help="UUID of the Organization to issue the token for")
        parser.add_argument("--name", default="", help="Optional label for this token")

    def handle(self, *args, **options):
        try:
            org = Organization.objects.get(pk=options["org_id"])
        except (Organization.DoesNotExist, ValueError) as exc:
            raise CommandError(f"No organization with id {options['org_id']!r}") from exc

        token, plaintext = MCPToken.generate(org, name=options["name"])

        self.stdout.write(f"Org: {org.id} ({org.name})")
        self.stdout.write(f"Token id: {token.id}")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(plaintext))
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "This secret is shown once and cannot be recovered. Store it now (e.g. as "
                "MCP_TOKEN in your Claude Desktop config)."
            )
        )
