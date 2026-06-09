from datetime import timedelta
from pathlib import Path

from corsheaders.defaults import default_headers
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,backend,draftly.software,.up.railway.app",
    cast=Csv(),
)
SENTRY_DSN = config("SENTRY_DSN", default="")

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=config(
            "SENTRY_ENVIRONMENT",
            default="development" if DEBUG else "production",
        ),
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0, cast=float),
        send_default_pii=config("SENTRY_SEND_DEFAULT_PII", default=False, cast=bool),
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    # local
    "apps.accounts",
    "apps.documents",
    "apps.proposals",
    "apps.core",
    "apps.billing",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "apps.core.middleware.AdminIPAllowlistMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Comma-separated IPs/CIDRs allowed to reach /admin/. Empty disables the gate
# (e.g. local dev). Example: "203.0.113.5,198.51.100.0/24".
ADMIN_IP_ALLOWLIST = config("ADMIN_IP_ALLOWLIST", default="")
# Number of trusted reverse proxies in front of Django. Required for
# `AdminIPAllowlistMiddleware` to safely consult X-Forwarded-For; if 0, only
# REMOTE_ADDR is trusted and XFF is ignored. Railway/Vercel edge typically = 1.
ADMIN_TRUSTED_PROXY_COUNT = config("ADMIN_TRUSTED_PROXY_COUNT", default=0, cast=int)

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

_database_url = config("DATABASE_URL", default="")
if _database_url:
    import dj_database_url

    DATABASES = {"default": dj_database_url.parse(_database_url, conn_max_age=0)}
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"]["options"] = "-c statement_timeout=30000"
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="rfp_db"),
            "USER": config("DB_USER", default="rfp_user"),
            "PASSWORD": config("DB_PASSWORD", default="rfp_pass"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Defaults — anonymous + authenticated baseline.
        "anon": config("THROTTLE_ANON", default="30/min"),
        "user": config("THROTTLE_USER", default="240/min"),
        # Scoped throttles — applied via ScopedRateThrottle on individual views.
        "auth_login": config("THROTTLE_AUTH_LOGIN", default="10/min"),
        "auth_register": config("THROTTLE_AUTH_REGISTER", default="5/hour"),
        "password_change": config("THROTTLE_PASSWORD_CHANGE", default="5/hour"),
        "proposal_generate": config("THROTTLE_PROPOSAL_GENERATE", default="20/hour"),
        "document_upload": config("THROTTLE_DOCUMENT_UPLOAD", default="30/hour"),
        "billing_checkout": config("THROTTLE_BILLING_CHECKOUT", default="10/hour"),
        "password_reset": config("THROTTLE_PASSWORD_RESET", default="5/hour"),
    },
}

# Cache backend — required by DRF throttling. Redis if available, else local memory.
_throttle_cache_url = config("REDIS_URL", default="")
if _throttle_cache_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _throttle_cache_url,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "draftly-default",
        }
    }

# JWT — short-lived access token, refresh rotated on use.
# Access lifetime kept short to limit exposure if a token is captured;
# the SPA refreshes silently via the axios 401 → refresh interceptor.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_LIFETIME_MINUTES", default=30, cast=int),
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_LIFETIME_DAYS", default=7, cast=int),
    ),
    "ROTATE_REFRESH_TOKENS": True,
    # BLACKLIST_AFTER_ROTATION requires the token_blacklist app + migration;
    # leave disabled until that's wired so refresh flow doesn't break.
}

DEFAULT_CORS_ALLOWED_ORIGINS = [
    "https://draftly.software",
    "https://www.draftly.software",
    "https://draftly-three.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# CORS
_cors_origins = config(
    "CORS_ALLOWED_ORIGINS",
    default=",".join(DEFAULT_CORS_ALLOWED_ORIGINS),
)
if _cors_origins.strip() == "*":
    CORS_ALLOW_ALL_ORIGINS = True
else:
    configured_cors_origins = [o.strip().rstrip("/") for o in _cors_origins.split(",") if o.strip()]
    CORS_ALLOWED_ORIGINS = list(
        dict.fromkeys([*DEFAULT_CORS_ALLOWED_ORIGINS, *configured_cors_origins])
    )

CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(DEFAULT_CORS_ALLOWED_ORIGINS))
CORS_ALLOW_HEADERS = list(default_headers) + [
    "baggage",
    "sentry-trace",
]

# Production security headers — only enabled when DEBUG is off so local dev
# (http://localhost) is unaffected. SECURE_PROXY_SSL_HEADER is required
# because Railway / Vercel terminate TLS upstream of Django.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = False  # frontend reads csrftoken cookie for header
    SECURE_REFERRER_POLICY = "same-origin"
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

# Celery
CELERY_BROKER_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

# File storage — local by default, Supabase Storage in production
USE_SUPABASE_STORAGE = config("USE_SUPABASE_STORAGE", default=False, cast=bool)
if USE_SUPABASE_STORAGE:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

    # Supabase Storage uses an S3-compatible API
    AWS_ACCESS_KEY_ID = config("SUPABASE_STORAGE_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY = config("SUPABASE_STORAGE_SECRET_KEY")
    AWS_STORAGE_BUCKET_NAME = config("SUPABASE_STORAGE_BUCKET")
    AWS_S3_REGION_NAME = config("SUPABASE_STORAGE_REGION", default="us-east-1")
    AWS_S3_ENDPOINT_URL = config("SUPABASE_STORAGE_ENDPOINT", default="")
    AWS_S3_ADDRESSING_STYLE = "path"
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_DEFAULT_ACL = "private"
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5 MB hard limit

# AI keys — free tiers, no credit card required
GOOGLE_AI_API_KEY = config("GOOGLE_AI_API_KEY")
GROQ_API_KEY = config("GROQ_API_KEY", default="")
GROQ_MODEL = config("GROQ_MODEL", default="llama-3.1-8b-instant")

# Cohere Rerank — free trial tier: 1000 calls/month, 10 req/min
COHERE_API_KEY = config("COHERE_API_KEY", default="")
COHERE_RERANK_MODEL = config("COHERE_RERANK_MODEL", default="rerank-english-v3.0")
RERANK_ENABLED = config("RERANK_ENABLED", default=True, cast=bool)
RERANK_FETCH_TOP_K = config("RERANK_FETCH_TOP_K", default=50, cast=int)
RERANK_KEEP_TOP_K = config("RERANK_KEEP_TOP_K", default=10, cast=int)

# Generation model (Google AI Studio free tier)
GEMINI_MODEL = config("GEMINI_MODEL", default="gemini-2.5-flash")

# Anthropic Claude — primary provider (Haiku 4.5 default, ~$0.008/proposal)
ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")
CLAUDE_MODEL = config("CLAUDE_MODEL", default="claude-haiku-4-5-20251001")
CLAUDE_ENABLED = config("CLAUDE_ENABLED", default=True, cast=bool)

# Embeddings — Google AI Studio (free tier, same key as generation)
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIMS = 768

# Stripe billing
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_API_VERSION = config("STRIPE_API_VERSION", default="2024-11-20.acacia")
STRIPE_PRICE_SOLO_MONTHLY = config("STRIPE_PRICE_SOLO_MONTHLY", default="")
STRIPE_PRICE_SOLO_ANNUAL = config("STRIPE_PRICE_SOLO_ANNUAL", default="")
STRIPE_PRICE_STUDIO_MONTHLY = config("STRIPE_PRICE_STUDIO_MONTHLY", default="")
STRIPE_PRICE_STUDIO_ANNUAL = config("STRIPE_PRICE_STUDIO_ANNUAL", default="")
STRIPE_PRICE_AGENCY_MONTHLY = config("STRIPE_PRICE_AGENCY_MONTHLY", default="")
STRIPE_PRICE_AGENCY_ANNUAL = config("STRIPE_PRICE_AGENCY_ANNUAL", default="")

# Public URL of the frontend; used for Stripe redirects after checkout/portal.
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173").rstrip("/")

# Google OAuth
GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID", default="")

# RFP input validation thresholds
# Email — SMTP in prod, console in dev
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="smtp.resend.com")
EMAIL_PORT = config("EMAIL_PORT", default=465, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="resend")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="Draftly <noreply@draftly.software>")
PASSWORD_RESET_TIMEOUT = 3600  # token valid 1 hour

RFP_MIN_CHARS = config("RFP_MIN_CHARS", default=200, cast=int)
RFP_MIN_WORDS = config("RFP_MIN_WORDS", default=30, cast=int)
RFP_MAX_CHARS = config("RFP_MAX_CHARS", default=200_000, cast=int)
RFP_INTENT_CHECK_ENABLED = config("RFP_INTENT_CHECK_ENABLED", default=True, cast=bool)
RFP_INTENT_MIN_CONFIDENCE = config("RFP_INTENT_MIN_CONFIDENCE", default=0.7, cast=float)
