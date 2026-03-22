from pathlib import Path
from datetime import timedelta
import os
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")

DEBUG = False

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "axes",

    "common",
    "users",
    "academics",
    "admission",
    "finance",
    "paie",
    "communication",
    "attendance",
    "core",
    "comptabilite",
    "events",
    "bibliotheque",
    "transport",
    "storages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "common.middlewares.SecurityHeadersMiddleware",
    "common.middlewares.RequestProfilingMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "axes.middleware.AxesMiddleware",
    "common.middlewares.AcademicYearCookieMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.debug","django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]},
    }
] 

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'USER': config('DB_USER'),
        'NAME': config('DB_NAME'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', cast=int),
        'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=60, cast=int),
    }
}

AUTH_PASSWORD_VALIDATORS = [
 {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
 {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
 {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
 {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Kinshasa"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Configuration du stockage des fichiers (Médias)
if config('USE_S3', cast=bool, default=False):
    # Stockage S3 (Supabase Storage, AWS S3, Backblaze B2...)
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='')
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default='')
else:
    # Stockage local (Environnement de dev ou persistant)
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",

    "DEFAULT_AUTHENTICATION_CLASSES": [
        "common.authentication.CookieJWTAuthentication",
    ],

    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],

    # Throttling de base overridé par config/settings/throttling.py
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],

    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "auth": "10/minute",
        "uploads": "50/hour",
        "exports": "20/hour",
        "notifications": "100/hour",
    },
}




AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "common.backends.MultiFieldAuthBackend",
]

INSTALLED_APPS += ["rest_framework_simplejwt.token_blacklist"]
INSTALLED_APPS += ["django_celery_beat"]
INSTALLED_APPS += ["channels"]

ASGI_APPLICATION = "config.asgi.application"




CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

# ─── Configuration du Cache Redis ────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,   # secondes
            "SOCKET_TIMEOUT": 5,           # secondes
            "IGNORE_EXCEPTIONS": True,     # Ne pas crasher si Redis est down
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        },
        "KEY_PREFIX": "schoolapi",
        "TIMEOUT": 300,   # 5 minutes par défaut
    }
}

# Durée de session via Redis
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"


ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost",
    cast=lambda v: [s.strip() for s in v.split(",")]
)

# Indique à Django qu'il est derrière un proxy HTTPS (Render)
# Cela répare les URL Swagger générées en `http://` qui bloquaient l'affichage (Mixed Content)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True



# SPECTACULAR_SETTINGS : configuration dans config/settings/swagger.py

# ─── Import des configurations modulaires ─────────────────────────────────────
from .axes import *  # noqa: F401,F403 - Protection brute force
from .celery import *  # noqa: F401,F403 - Configuration Celery
from .pagination import (  # Pagination par défaut
    PAGINATION_SETTINGS,
    REST_FRAMEWORK as _PAGINATION_REST_FRAMEWORK,
)

# Merge pagination into existing REST_FRAMEWORK without overwriting schema config.
REST_FRAMEWORK.update(_PAGINATION_REST_FRAMEWORK)

# ====== RENDER GRATUIT ======
# Si aucun worker Celery n'est payé/disponible, on exécute les tâches en direct.
# Vous pourrez mettre USE_CELERY_WORKER=True dans Render si vous passez en Pro.
if not config('USE_CELERY_WORKER', default=False, cast=bool):
    CELERY_TASK_ALWAYS_EAGER = True
