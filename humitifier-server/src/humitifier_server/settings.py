"""
Django settings for humitifier_server project.

Generated by 'django-admin startproject' using Django 5.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
from . import env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-ffdjavjsp%s%b069$aai#h7odtbd#!q8uu7=hn1tv&y$gdq17_"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.get_boolean("DJANGO_DEBUG", False)

ALLOWED_HOSTS = []
INTERNAL_IPS = ["127.0.0.1",]

_env_hosts = env.get("DJANGO_ALLOWED_HOSTS", default=None)
if _env_hosts:
    ALLOWED_HOSTS += _env_hosts.split(",")


# Application definition

INSTALLED_APPS = [
    # Local apps with overrides here
    "main",
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.forms",
    # Third-party apps
    "rest_framework",
    "simple_menu",
    # Local apps
    "hosts",
    "api",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


if DEBUG:
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")

ROOT_URLCONF = "humitifier_server.urls"

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
                "main.context_processors.layout_context"
            ],
        },
    },
]

FORM_RENDERER = "main.forms.CustomFormRenderer"

WSGI_APPLICATION = "humitifier_server.wsgi.application"

# Auth
AUTH_USER_MODEL = "main.User"

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.get("POSTGRES_DB", default="postgres"),
        "USER": env.get("POSTGRES_USER", default="postgres"),
        "PASSWORD": env.get("POSTGRES_PASSWORD", default="postgres"),
        "HOST": env.get("POSTGRES_HOST", default="127.0.0.1"),
        "PORT": env.get("POSTGRES_PORT", default="5432"),
    }
}


# Security

_https_enabled = env.get_boolean("DJANGO_HTTPS", default=False)

X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = _https_enabled

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = _https_enabled
CSRF_COOKIE_SECURE = _https_enabled
# Needed to work in kubernetes, as the app may be behind a proxy/may not know it's
# own domain
SESSION_COOKIE_DOMAIN = env.get("SESSION_COOKIE_DOMAIN", default=None)
CSRF_COOKIE_DOMAIN = env.get("CSRF_COOKIE_DOMAIN", default=None)
SESSION_COOKIE_NAME = env.get("SESSION_COOKIE_NAME",
                              default="humitifier_sessionid")
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 60 * 60 * 12  # 12 hours

CSRF_TRUSTED_ORIGINS = [
    f"http{'s' if _https_enabled else ''}://{host}" for host in ALLOWED_HOSTS
]

# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env.get("LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env.get("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Amsterdam"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Whitenoise

STATIC_ROOT = BASE_DIR / "static"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}