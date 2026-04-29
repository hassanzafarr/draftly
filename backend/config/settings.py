from pathlib import Path
from decouple import config, Csv
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,backend", cast=Csv())

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

# CORS
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)

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

# Generation model (Google AI Studio free tier)
GEMINI_MODEL = config("GEMINI_MODEL", default="gemini-2.5-flash")

# Embeddings — Google AI Studio (free tier, same key as generation)
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIMS = 768
