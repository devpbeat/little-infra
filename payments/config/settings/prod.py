"""Production settings. All secrets and hosts come from the environment."""

from .base import *  # noqa: F401,F403

DEBUG = False

if not SECRET_KEY:  # noqa: F405
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production.")

if not ALLOWED_HOSTS:  # noqa: F405
    raise RuntimeError("ALLOWED_HOSTS must be set in production.")

# TLS terminates at Traefik; trust its forwarded-proto header so the SSL
# redirect doesn't loop on requests that are already HTTPS at the edge.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
