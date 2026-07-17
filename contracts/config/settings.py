"""Django settings for the contracts admin app."""
from pathlib import Path

import environ
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"]
)
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# --- Application definition -------------------------------------------------

INSTALLED_APPS = [
    # Unfold admin theme — must precede django.contrib.admin.
    "unfold",
    "unfold.contrib.forms",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "martor",
    "contracts_app",
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

# --- Database ---------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="contracts"),
        "USER": env("POSTGRES_USER", default="contracts"),
        "PASSWORD": env("POSTGRES_PASSWORD", default=""),
        "HOST": env("POSTGRES_HOST", default="contracts-postgres"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

# --- Auth -------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- I18N -------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

# --- Static files -----------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Behind Traefik TLS termination.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# --- Unfold admin theme -----------------------------------------------------

UNFOLD = {
    "SITE_TITLE": "Contracts",
    "SITE_HEADER": "Contracts",
    "SITE_SUBHEADER": "Clients, templates & signatures",
    "SITE_SYMBOL": "handshake",  # material symbol shown next to the title
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "THEME": None,  # let users toggle light/dark
    "BORDER_RADIUS": "8px",
    "COLORS": {
        "primary": {
            "50": "238 242 255",
            "100": "224 231 255",
            "200": "199 210 254",
            "300": "165 180 252",
            "400": "129 140 248",
            "500": "99 102 241",
            "600": "79 70 229",
            "700": "67 56 202",
            "800": "55 48 163",
            "900": "49 46 129",
            "950": "30 27 75",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Sales",
                "separator": True,
                "items": [
                    {
                        "title": "Clients",
                        "icon": "groups",
                        "link": reverse_lazy("admin:contracts_app_client_changelist"),
                    },
                    {
                        "title": "Contracts",
                        "icon": "handshake",
                        "link": reverse_lazy("admin:contracts_app_contract_changelist"),
                    },
                    {
                        "title": "Templates",
                        "icon": "description",
                        "link": reverse_lazy(
                            "admin:contracts_app_contracttemplate_changelist"
                        ),
                    },
                ],
            },
            {
                "title": "Administration",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                    },
                    {
                        "title": "Groups",
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
        ],
    },
}


# --- Martor (markdown editor) ----------------------------------------------

MARTOR_THEME = "bootstrap"
MARTOR_ENABLE_CONFIGS = {
    "emoji": "false",
    "imgur": "false",
    "mention": "false",
    "jquery": "true",
    "living": "false",
    "spellcheck": "false",
    "hljs": "true",
}
MARTOR_ENABLE_LABEL = True
MARTOR_UPLOAD_URL = ""  # disable image upload endpoint
MARTOR_SEARCH_USERS_URL = ""  # disable mention search
MARTOR_MARKDOWN_BASE_MENTION_URL = ""

# --- DocuSeal ---------------------------------------------------------------

DOCUSEAL_URL = env("DOCUSEAL_URL", default="http://docuseal:3000")
DOCUSEAL_PUBLIC_URL = env(
    "DOCUSEAL_PUBLIC_URL", default="https://sign.ignitesolutions.click"
)
DOCUSEAL_API_TOKEN = env("DOCUSEAL_API_TOKEN", default="")
DOCUSEAL_WEBHOOK_SECRET = env("DOCUSEAL_WEBHOOK_SECRET", default="")

# Owner (you) — the counter-signer added to every contract.
OWNER_SIGNER_NAME = env("OWNER_SIGNER_NAME", default="")
OWNER_SIGNER_EMAIL = env("OWNER_SIGNER_EMAIL", default="")

# --- MinIO / S3 -------------------------------------------------------------

MINIO_ENDPOINT = env("MINIO_ENDPOINT", default="http://minio:9000")
MINIO_PUBLIC_ENDPOINT = env(
    "MINIO_PUBLIC_ENDPOINT", default="https://minio.ignitesolutions.click"
)
MINIO_ACCESS_KEY = env("MINIO_ACCESS_KEY", default="minioadmin")
MINIO_SECRET_KEY = env("MINIO_SECRET_KEY", default="minioadmin123")
MINIO_BUCKET = env("MINIO_BUCKET", default="contracts")

# --- Logging ----------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "contracts_app": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
