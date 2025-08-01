from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

DOMAIN = config("DOMAIN")
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
ENV = config("ENV")

ALLOWED_HOSTS = ["fbsurvivor.com"]
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CSRF_TRUSTED_ORIGINS = ["https://fbsurvivor.com"]

INTERNAL_IPS = ["127.0.0.1"]

CONTACT = config("CONTACT", "")
VENMO = config("VENMO", "")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "fbsurvivor.core",
]


MIDDLEWARE = [
    "django.middleware.gzip.GZipMiddleware",
    "htmlmin.middleware.HtmlMinifyMiddleware",
    "htmlmin.middleware.MarkRequestMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "fbsurvivor.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR, "fbsurvivor/templates"],
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

WSGI_APPLICATION = "fbsurvivor.wsgi.application"

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": config("PGDATABASE"),
        "USER": config("PGUSER"),
        "PASSWORD": config("PGPASSWORD"),
        "HOST": config("PGHOST", default="127.0.0.1"),
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True
SESSION_CACHE_ALIAS = "default"

CACHE_TTL = 60 * 15

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa
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
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Los_Angeles"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

HTML_MINIFY = True
STATICFILES_DIRS = [BASE_DIR / "fbsurvivor/static"]
STATIC_URL = "/static/"
STATIC_ROOT = "/srv/www/fbsurvivor/static/"  # noqa

SMTP_SERVER = config("SMTP_SERVER", "", cast=str)
SMTP_SENDER = config("SMTP_SENDER", "", cast=str)
SMTP_USER = config("SMTP_USER", "", cast=str)
SMTP_PASSWORD = config("SMTP_PASSWORD", "", cast=str)
SMTP_PORT = config("SMTP_PORT", 465)

if ENV == "dev":
    DEBUG = True
    ALLOWED_HOSTS = ["*"]
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")
