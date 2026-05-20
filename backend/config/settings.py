from pathlib import Path
from decouple import config, Csv
from datetime import timedelta
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,backend,draftly.software,.up.railway.app", cast=Csv())
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
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

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
}

# JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
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
    configured_cors_origins = [
        o.strip().rstrip("/") for o in _cors_origins.split(",") if o.strip()
    ]
    CORS_ALLOWED_ORIGINS = list(
        dict.fromkeys([*DEFAULT_CORS_ALLOWED_ORIGINS, *configured_cors_origins])
    )

CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(DEFAULT_CORS_ALLOWED_ORIGINS))
CORS_ALLOW_HEADERS = list(default_headers) + [
    "baggage",
    "sentry-trace",
]

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
STRIPE_PRICE_GROWTH = config("STRIPE_PRICE_GROWTH", default="")   # $29/mo recurring Price ID
STRIPE_PRICE_AGENCY = config("STRIPE_PRICE_AGENCY", default="")   # $99/mo recurring Price ID

# RFP input validation thresholds
RFP_MIN_CHARS = config("RFP_MIN_CHARS", default=200, cast=int)
RFP_MIN_WORDS = config("RFP_MIN_WORDS", default=30, cast=int)
RFP_MAX_CHARS = config("RFP_MAX_CHARS", default=200_000, cast=int)
RFP_INTENT_CHECK_ENABLED = config("RFP_INTENT_CHECK_ENABLED", default=True, cast=bool)
RFP_INTENT_MIN_CONFIDENCE = config("RFP_INTENT_MIN_CONFIDENCE", default=0.7, cast=float)
