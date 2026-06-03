"""Test-only Django settings.

Inherits everything from `config.settings` but overrides anything that would
hit production infrastructure (DB pooler, real LLM APIs, persistent storage).

Activated via `DJANGO_SETTINGS_MODULE=config.test_settings` (set in pyproject.toml).
"""

import os

# Set safe placeholders for required env vars BEFORE importing settings.py.
# Without this, python-decouple raises on `config("SECRET_KEY")` if .env is
# missing in the test runner CWD.
os.environ.setdefault("SECRET_KEY", "test-secret-not-for-production")
os.environ.setdefault("DEBUG", "False")
os.environ.setdefault("GOOGLE_AI_API_KEY", "test-google-key")
os.environ.setdefault("DATABASE_URL", "")  # force fall-through to DB_* vars

from config.settings import *  # noqa: E402, F401, F403

# Local Postgres for tests — never touch the production pooler.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("TEST_DB_NAME", "draftly_test"),
        "USER": os.environ.get("TEST_DB_USER", "rfp_user"),
        "PASSWORD": os.environ.get("TEST_DB_PASSWORD", "rfp_pass"),
        "HOST": os.environ.get("TEST_DB_HOST", "localhost"),
        "PORT": os.environ.get("TEST_DB_PORT", "5432"),
        "TEST": {"NAME": os.environ.get("TEST_DB_NAME", "draftly_test")},
    }
}

# Run Celery tasks inline so .delay() calls execute synchronously in-process.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable third-party API keys to guarantee tests never reach the network.
GOOGLE_AI_API_KEY = "test-google-key"
ANTHROPIC_API_KEY = ""
CLAUDE_ENABLED = False
GROQ_API_KEY = ""
COHERE_API_KEY = ""
RERANK_ENABLED = False

# Faster password hashing for tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Quiet Sentry in tests.
SENTRY_DSN = ""

# Never redirect HTTP→HTTPS in tests (test client uses HTTP).
SECURE_SSL_REDIRECT = False

# Disable rate limiting in tests — rates would otherwise trip across rapid runs.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405 — imported via `from config.settings import *`
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}
