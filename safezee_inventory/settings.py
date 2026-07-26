"""
Django settings for safezee_inventory project.

SAFEZEE Inventory — single-user internal tool for SAFEZEE Fire Protection.
No authentication, no multi-tenant concerns.
"""

import os
from pathlib import Path

# Optional: load a local .env file during development.
# pip install python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------
# SECURITY
# ------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-CHANGE-THIS-IN-PRODUCTION-safezee-fire-protection",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

# ------------------------------------------------------------------
# APPLICATION DEFINITION
# ------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local apps
    "accounts.apps.AccountsConfig",
    "inventory.apps.InventoryConfig",
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
    "accounts.middleware.PasskeyAuthMiddleware",
]

ROOT_URLCONF = "safezee_inventory.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "safezee_inventory.wsgi.application"

# ------------------------------------------------------------------
# DATABASE — Neon PostgreSQL
# ------------------------------------------------------------------
# Set DATABASE_URL in your environment, e.g.:
# postgresql://user:password@ep-xxxx.neon.tech/safezee_inventory?sslmode=require
#
# pip install dj-database-url psycopg2-binary
import dj_database_url

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    # Fallback so `manage.py` commands don't hard-crash if the env var
    # is missing — but you MUST set DATABASE_URL for this project to work.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "safezee_inventory"),
            "USER": os.environ.get("DB_USER", "postgres"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "OPTIONS": {"sslmode": "require"},
        }
    }

# ------------------------------------------------------------------
# PASSWORD VALIDATION — kept minimal, no user-facing auth in this app
# ------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = []

CSRF_TRUSTED_ORIGINS = [
    "https://inventory.safezeefire.com",
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True

    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ------------------------------------------------------------------
# INTERNATIONALIZATION
# ------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------
# STATIC FILES
# ------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------
# PASSKEY (WebAuthn) AUTHENTICATION
# ------------------------------------------------------------------
# PASSKEY_RP_ID must be the exact domain hosting the site — NOT a URL,
# NOT an IP address, no port. For local dev use "localhost".
# In production this MUST match your real domain, e.g. "inventory.safezee.in",
# and the site must be served over HTTPS (browsers block WebAuthn on
# plain HTTP for anything other than localhost).
PASSKEY_RP_ID = os.environ.get("PASSKEY_RP_ID", "localhost")
PASSKEY_RP_NAME = os.environ.get("PASSKEY_RP_NAME", "SAFEZEE Inventory")

# PASSKEY_ORIGIN must be the exact scheme + host + port the browser
# shows in its address bar, e.g. "https://inventory.safezee.in" or
# "http://localhost:8000" for local dev. Must match exactly, including
# http vs https and the port.
PASSKEY_ORIGIN = os.environ.get("PASSKEY_ORIGIN", "http://localhost:8000")

# A shared secret required to register a NEW passkey. Without this,
# anyone who finds the /accounts/register/ page could add their own
# device and gain access. Set a long random value in production and
# only share it with yourself when enrolling a new device — you can
# rotate it any time by changing the env var.
PASSKEY_ENROLLMENT_SECRET = os.environ.get("PASSKEY_ENROLLMENT_SECRET", "")
