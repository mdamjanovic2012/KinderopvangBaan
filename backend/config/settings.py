from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
import os

load_dotenv()

try:
    from config.config_local import *
    LOCAL = True
except ImportError:
    LOCAL = False

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",

    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",

    # local
    "users",
    "institutions",
    "jobs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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

_db_url = os.getenv("DATABASE_URL")
if _db_url:
    DATABASES = {
        "default": dj_database_url.parse(
            _db_url,
            engine="django.contrib.gis.db.backends.postgis",
            conn_max_age=600,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": os.getenv("DB_NAME", "kinderopvangbaan"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "nl-nl"
TIME_ZONE = "Europe/Amsterdam"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# django-unfold — owner dashboard at /pivce-za-zivce
# ---------------------------------------------------------------------------
from django.urls import reverse_lazy

UNFOLD = {
    "SITE_TITLE": "KinderopvangBaan Beheer",
    "SITE_HEADER": "KinderopvangBaan",
    "SITE_URL": "/",
    "SITE_ICON": None,
    "SITE_SYMBOL": "work",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "primary": {
            "50": "240 249 255",
            "100": "224 242 254",
            "200": "186 230 253",
            "300": "125 211 252",
            "400": "56 189 248",
            "500": "14 165 233",
            "600": "2 132 199",
            "700": "3 105 161",
            "800": "7 89 133",
            "900": "12 74 110",
            "950": "8 47 73",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Overzicht",
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": "Organisaties",
                "items": [
                    {
                        "title": "Alle organisaties",
                        "icon": "business",
                        "link": reverse_lazy("admin:institutions_institution_changelist"),
                    },
                    {
                        "title": "Reviews",
                        "icon": "star",
                        "link": reverse_lazy("admin:institutions_review_changelist"),
                    },
                ],
            },
            {
                "title": "Vacatures",
                "items": [
                    {
                        "title": "Alle vacatures",
                        "icon": "work",
                        "link": reverse_lazy("admin:jobs_job_changelist"),
                    },
                    {
                        "title": "Sollicitaties",
                        "icon": "send",
                        "link": reverse_lazy("admin:jobs_jobapplication_changelist"),
                    },
                ],
            },
            {
                "title": "Gebruikers",
                "items": [
                    {
                        "title": "Alle gebruikers",
                        "icon": "people",
                        "link": reverse_lazy("admin:users_user_changelist"),
                    },
                    {
                        "title": "Werkzoekende profielen",
                        "icon": "person_search",
                        "link": reverse_lazy("admin:users_workerprofile_changelist"),
                    },
                ],
            },
        ],
    },
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardPagination",
    "PAGE_SIZE": 20,
}

CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
).split(",")

# GeoDjango — library paths (env vars override, then platform defaults)
import platform
_gdal = os.getenv("GDAL_LIBRARY_PATH")
_geos = os.getenv("GEOS_LIBRARY_PATH")
if _gdal:
    GDAL_LIBRARY_PATH = _gdal
elif platform.system() == "Darwin":
    GDAL_LIBRARY_PATH = "/opt/homebrew/lib/libgdal.dylib"
if _geos:
    GEOS_LIBRARY_PATH = _geos
elif platform.system() == "Darwin":
    GEOS_LIBRARY_PATH = "/opt/homebrew/lib/libgeos_c.dylib"
