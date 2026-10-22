"""
Django settings for Brakastølen (Tranberg Utvikling AS).

Every value that differs between your computer and the live server is read
from the `.env` file in the project root (see `.env.example` for all options).
This file itself never needs to change between environments.

Safety rules built in:
- With DEBUG=False the site refuses to start without a strong SECRET_KEY and
  a real ALLOWED_HOSTS list, so a missing .env can never go live insecurely.
- HTTPS, secure cookies, HSTS and security headers are switched on
  automatically in production.
- The database is SQLite until DB_NAME is filled in; then it's PostgreSQL.
- The site sends no e-mail; every inquiry is saved in the dashboard.

Check the live configuration with:  python manage.py check --deploy
"""

import os
import secrets
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load `.env` into the environment. Real environment variables (set by the
# server or hosting panel) always win over values in the file.
load_dotenv(BASE_DIR / '.env')


def env(key, default=None):
    value = os.environ.get(key)
    return default if value in (None, '') else value


def env_bool(key, default=False):
    value = os.environ.get(key)
    if value in (None, ''):
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def env_int(key, default=0):
    value = os.environ.get(key)
    if value in (None, ''):
        return default
    try:
        return int(value)
    except ValueError:
        raise ImproperlyConfigured(f'{key} must be a whole number, got "{value}".')


def env_list(key, default=''):
    value = os.environ.get(key) or default
    return [item.strip() for item in value.split(',') if item.strip()]


# ------------------------------------------------------------------
# Core / environment
# ------------------------------------------------------------------

# Never True on the live server: it shows code and settings on error pages.
DEBUG = env_bool('DEBUG', False)

# Public address of the site – used for canonical URLs, sitemap, structured data
# and the list of trusted origins below. The domain has an "ø", so it is written
# the way browsers send it (punycode): www.brakastølen.no = www.xn--brakastlen-6cb.no
SITE_URL = env('SITE_URL', 'https://www.xn--brakastlen-6cb.no').rstrip('/')

# False on test/staging domains: search engines are told not to index anything
# (robots.txt blocks all, plus noindex header and meta tag on every page).
ALLOW_INDEXING = env_bool('ALLOW_INDEXING', True)

INSECURE_KEY_MARKERS = ('django-insecure', 'change-me', 'changeme', 'secret')

SECRET_KEY = env('SECRET_KEY', '')
if DEBUG:
    if not SECRET_KEY:
        # Local convenience only: a new key each start logs you out on restart.
        SECRET_KEY = secrets.token_urlsafe(64)
else:
    if len(SECRET_KEY) < 50 or any(marker in SECRET_KEY.lower() for marker in INSECURE_KEY_MARKERS):
        raise ImproperlyConfigured(
            'SECRET_KEY is missing or too weak. Generate one with:\n'
            '  python -c "import secrets; print(secrets.token_urlsafe(64))"\n'
            'and put it in .env as SECRET_KEY=...'
        )

# Keys that were used before and should still validate old sessions/links
# while you rotate SECRET_KEY (comma separated).
SECRET_KEY_FALLBACKS = env_list('SECRET_KEY_FALLBACKS')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]' if DEBUG else '')
if not DEBUG and (not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS must list the real domain names when DEBUG=False, e.g. '
        'ALLOWED_HOSTS=www.xn--brakastlen-6cb.no,xn--brakastlen-6cb.no,www.brakastolen.no,brakastolen.no'
    )

# Sites allowed to submit forms (needed for HTTPS POST requests).
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS') or (
    [SITE_URL, SITE_URL.replace('://www.', '://')] if not DEBUG else []
)

INSTALLED_APPS = [
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'apps.core',
    'apps.blog',
    'apps.dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'apps.core.middleware.SecurityHeadersMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.dashboard.context_processors.dashboard',
                'apps.core.context_processors.seo',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

SITE_ID = 1


# ------------------------------------------------------------------
# Database
# SQLite until DB_NAME is set in .env – then PostgreSQL, with no code change.
# ------------------------------------------------------------------

if env('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER', ''),
            'PASSWORD': env('DB_PASSWORD', ''),
            'HOST': env('DB_HOST', 'localhost'),
            'PORT': env('DB_PORT', '5432'),
            # Keep connections open between requests (seconds) and check they're alive.
            'CONN_MAX_AGE': env_int('DB_CONN_MAX_AGE', 60),
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': {
                # 'require' when the database is on another machine, 'prefer' on the same server.
                'sslmode': env('DB_SSLMODE', 'prefer'),
                'connect_timeout': env_int('DB_CONNECT_TIMEOUT', 10),
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': env('SQLITE_PATH', str(BASE_DIR / 'db.sqlite3')),
            'OPTIONS': {
                # Wait for a lock instead of failing with "database is locked".
                'timeout': 20,
                # Writes take the lock up front, so two gunicorn workers saving at once queue
                # instead of one of them failing halfway through.
                'transaction_mode': 'IMMEDIATE',
                # WAL: visitors keep reading while the dashboard writes. NORMAL is safe with WAL
                # and much faster than the default FULL.
                'init_command': 'PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;',
            },
        }
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ------------------------------------------------------------------
# Authentication and passwords
# ------------------------------------------------------------------

LOGIN_URL = '/dashboard/login/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Strongest hashers first. Scrypt is built into Python; existing passwords
# are upgraded automatically the next time each user logs in.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.ScryptPasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

# Password reset links stop working after 1 hour.
PASSWORD_RESET_TIMEOUT = 60 * 60


# ------------------------------------------------------------------
# HTTPS, cookies and security headers
# ------------------------------------------------------------------

# True on the live server. Set HTTPS=False only for a staging server without a certificate.
HTTPS = env_bool('HTTPS', not DEBUG)

# Most hosts (nginx, Caddy, Render, Railway, cPanel ...) handle HTTPS in front of
# Django and tell it with X-Forwarded-Proto. Set BEHIND_PROXY=False if Django
# faces the internet directly.
if env_bool('BEHIND_PROXY', True):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = HTTPS

# HSTS: browsers remember to only ever use HTTPS for this domain.
# Start with a short value when first going live, then raise it (1 year = 31536000).
SECURE_HSTS_SECONDS = env_int('SECURE_HSTS_SECONDS', 31536000) if HTTPS else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', False)

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# A stale contact form gets its text back with a fresh token instead of a bare 403 page.
CSRF_FAILURE_VIEW = 'apps.core.views.csrf_failure'

# Cookies: only sent over HTTPS, hidden from JavaScript, not sent with cross-site requests.
SESSION_COOKIE_SECURE = HTTPS
CSRF_COOKIE_SECURE = HTTPS
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True  # JavaScript reads the token from the form, not the cookie
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
# The __Host- prefix makes browsers reject the cookie unless it's secure and
# locked to this exact domain – it can't be set by a subdomain or over HTTP.
if HTTPS:
    SESSION_COOKIE_NAME = '__Host-sessionid'
    CSRF_COOKIE_NAME = '__Host-csrftoken'

SESSION_COOKIE_AGE = env_int('SESSION_COOKIE_AGE', 60 * 60 * 24)  # 1 day

# Content-Security-Policy: the only places scripts, styles, fonts and images may come from.
# Add a domain here if you embed something new (e.g. a map or video player).
CSP_ENABLED = env_bool('CSP_ENABLED', True)
CSP_REPORT_ONLY = env_bool('CSP_REPORT_ONLY', False)
CONTENT_SECURITY_POLICY = {
    'default-src': ["'self'"],
    'script-src': ["'self'", "'unsafe-inline'", 'https://kit.fontawesome.com', 'https://*.fontawesome.com'],
    'style-src': ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com', 'https://*.fontawesome.com'],
    'font-src': ["'self'", 'data:', 'https://fonts.gstatic.com', 'https://*.fontawesome.com'],
    'img-src': ["'self'", 'data:', 'blob:'],
    'media-src': ["'self'", 'blob:'],
    'connect-src': ["'self'", 'https://*.fontawesome.com'],
    'frame-src': ["'none'"],
    'frame-ancestors': ["'none'"],
    'object-src': ["'none'"],
    'base-uri': ["'self'"],
    'form-action': ["'self'"],
    'manifest-src': ["'self'"],
    'worker-src': ["'self'", 'blob:'],
}
if HTTPS:
    CONTENT_SECURITY_POLICY['upgrade-insecure-requests'] = []

# Google Analytics 4, e.g. G-XXXXXXXXXX. Empty = no analytics and no cookie banner.
# When set, analytics only loads after the visitor accepts cookies (Consent Mode v2).
GA_MEASUREMENT_ID = env('GA_MEASUREMENT_ID', '')
if GA_MEASUREMENT_ID:
    CONTENT_SECURITY_POLICY['script-src'] += ['https://www.googletagmanager.com']
    CONTENT_SECURITY_POLICY['img-src'] += ['https://*.google-analytics.com', 'https://*.googletagmanager.com']
    CONTENT_SECURITY_POLICY['connect-src'] += [
        'https://*.google-analytics.com', 'https://*.analytics.google.com', 'https://*.googletagmanager.com',
    ]

# Name of the cookie that stores the visitor's cookie choice ("all" or "necessary").
COOKIE_CONSENT_NAME = 'brakastolen_cookie_consent'

# Browser features the site never uses are switched off for it and anything it embeds.
PERMISSIONS_POLICY = {
    'camera': [],
    'microphone': [],
    'geolocation': [],
    'payment': [],
    'usb': [],
    'magnetometer': [],
    'gyroscope': [],
    'accelerometer': [],
    'interest-cohort': [],
    'browsing-topics': [],
}


# ------------------------------------------------------------------
# Uploads
# ------------------------------------------------------------------

# Form fields (not files) larger than this are rejected – stops oversized POST attacks.
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int('DATA_UPLOAD_MAX_MEMORY_SIZE', 5 * 1024 * 1024)  # 5 MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000
DATA_UPLOAD_MAX_NUMBER_FILES = env_int('DATA_UPLOAD_MAX_NUMBER_FILES', 50)
# Files larger than this are streamed to disk instead of kept in memory.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5 MB
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755


# ------------------------------------------------------------------
# E-mail – the site sends none. Every inquiry is saved in the dashboard
# (/dashboard/henvendelser/); notices will come through a Zapier webhook later.
# ------------------------------------------------------------------

# Even a stray send_mail() (e.g. Django's password reset) goes nowhere
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'


# ------------------------------------------------------------------
# Cache (used for llms-full.txt and the contact form rate limit). One process = local memory.
# ------------------------------------------------------------------

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'brakastolen',
    }
}


# ------------------------------------------------------------------
# Internationalization
# ------------------------------------------------------------------

LANGUAGE_CODE = 'nb-no'
TIME_ZONE = 'Europe/Oslo'
USE_I18N = True
USE_TZ = True


# ------------------------------------------------------------------
# Static & media files
# ------------------------------------------------------------------

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# On the live server every static file gets a content hash in its name (style.3f2a1c.css), so
# browsers may cache it for a year and still get the new file the moment it changes. It needs
# `collectstatic` to have run, so local development (DEBUG=True) keeps plain file names.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': ('django.contrib.staticfiles.storage.StaticFilesStorage' if DEBUG
                    else 'whitenoise.storage.CompressedManifestStaticFilesStorage'),
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ------------------------------------------------------------------
# Logging – console output, picked up by the server's process manager.
# ------------------------------------------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': env('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
