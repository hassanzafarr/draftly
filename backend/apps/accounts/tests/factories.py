import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import Organization, User


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: f"Org {n}")
    subscription_tier = Organization.Tier.FREE


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    role = User.Role.ADMIN
    org = factory.SubFactory(OrganizationFactory)

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        raw = extracted or "TestPass123!"
        self.set_password(raw)
        # cache the raw password for tests that need to log in
        self._raw_password = raw
        if create:
            self.save()
