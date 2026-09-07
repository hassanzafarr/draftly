from django.core.management.base import BaseCommand

from apps.accounts.demo import get_or_create_demo, reset_demo_data


class Command(BaseCommand):
    help = "Create (or reseed) the public demo organization used by the 'View Demo' login button."

    def handle(self, *args, **options):
        org, user = get_or_create_demo()
        self.stdout.write(f"Demo org: {org.id} ({org.name})")
        self.stdout.write(f"Demo user: {user.id} ({user.email})")
        reset_demo_data(org, user)
        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
