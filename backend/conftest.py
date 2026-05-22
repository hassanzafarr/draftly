"""Root pytest fixtures shared across all backend tests."""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture(autouse=True)
def _isolate_media_root(tmp_path_factory, settings):
    """Redirect MEDIA_ROOT to a per-session tmp dir so FileField writes don't pollute the repo."""
    settings.MEDIA_ROOT = str(tmp_path_factory.mktemp("media"))


@pytest.fixture
def api_client():
    """Unauthenticated DRF APIClient."""
    return APIClient()


@pytest.fixture
def org(db):
    from apps.accounts.tests.factories import OrganizationFactory
    return OrganizationFactory()


@pytest.fixture
def other_org(db):
    from apps.accounts.tests.factories import OrganizationFactory
    return OrganizationFactory(name="Other Org")


@pytest.fixture
def user(db, org):
    from apps.accounts.tests.factories import UserFactory
    return UserFactory(org=org)


@pytest.fixture
def other_user(db, other_org):
    from apps.accounts.tests.factories import UserFactory
    return UserFactory(org=other_org, email="other@example.com")


@pytest.fixture
def auth_client(api_client, user):
    """APIClient authenticated as `user` via JWT bearer token."""
    token = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    api_client.user = user
    return api_client


@pytest.fixture
def other_auth_client(other_user):
    """Second APIClient authenticated as a user in a different org."""
    client = APIClient()
    token = RefreshToken.for_user(other_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    client.user = other_user
    return client
