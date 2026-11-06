import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY")

TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

CREATE_SUPER_ADMIN = os.getenv("CREATE_SUPER_ADMIN", "False").lower() == "true"
SUPER_ADMIN_ACTIVITY = os.getenv("SUPER_ADMIN_ACTIVITY")
SUPER_ADMIN_NAME = os.getenv("SUPER_ADMIN_NAME")
SUPER_LAST_NAME = os.getenv("SUPER_LAST_NAME")
SUPER_FIRST_NAME = os.getenv("SUPER_FIRST_NAME")
SUPER_FATHER_NAME = os.getenv("SUPER_FATHER_NAME")
SUPER_PASSWORD = os.getenv("SUPER_PASSWORD")

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
    "corsheaders",
    "users",
    "management",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST") or "db",
        # DB_PORT из .env - это порт на хосте для доступа к БД из внешних программ, внутри docker-сети он всегда 5432
        "PORT": "5432",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "users.Employee"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("ACCESS_TOKEN_LIFETIME") or 5)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("REFRESH_TOKEN_LIFETIME") or 1)),
}

LANGUAGE_CODE = "ru-ru"

TIME_ZONE = os.getenv("LOCAL_TIME_ZONE") or "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = (BASE_DIR / "static",)
STATIC_ROOT = BASE_DIR / "staticfiles"

SPECTACULAR_SETTINGS = {
    "TITLE": "Easy Management API",
    "DESCRIPTION": "Easy Management API description",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    # Пустые элементы отбрасываются, иначе пустая переменная дала бы список [""]
    CORS_ALLOWED_ORIGINS = [origin for origin in (os.getenv("CORS_ALLOWED_ORIGINS") or "").split(",") if origin]
    CSRF_TRUSTED_ORIGINS = [origin for origin in (os.getenv("CSRF_TRUSTED_ORIGINS") or "").split(",") if origin]

# Redis. Имя хоста "redis" - это имя сервиса в docker compose, вне docker адреса задаются через переменные окружения
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("CACHE_URL") or "redis://redis:6379/1",
    }
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL") or "redis://redis:6379/2"
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND") or "redis://redis:6379/3"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = (os.getenv("CELERY_TASK_TRACK_STARTED") or "true").lower() == "true"
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT") or 600)
CHECK_INTERVAL = int(os.getenv("CELERY_EXPIRED_STATUS_CHECK_INTERVAL") or 30)
CELERY_BEAT_SCHEDULE = {
    "check_dead_line_set_expired": {
        "task": "management.tasks.check_dead_line_set_expired",
        "schedule": timedelta(minutes=CHECK_INTERVAL),
    }
}


if TEST_MODE:
    SECRET_KEY = "django-secret_test_key"
    DEBUG = True
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            # Django создает отдельную БД test_<NAME> и удаляет ее после тестов, рабочая БД не затрагивается.
            # Значения по умолчанию соответствуют сервису postgres в CI, где файла .env и переменных DB_* нет
            "NAME": os.getenv("DB_NAME") or "test_db",
            "USER": os.getenv("DB_USER") or "test_user",
            "PASSWORD": os.getenv("DB_PASSWORD") or "test_password",
            "HOST": "localhost",
            "PORT": os.getenv("DB_PORT") or "5432",
        }
    }
    CSRF_TRUSTED_ORIGINS = ["http://localhost", "https://localhost"]
    CORS_ALLOWED_ORIGINS = ["http://localhost", "https://localhost"]
