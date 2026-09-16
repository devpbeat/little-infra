"""ASGI entrypoint (not served in v1; gunicorn+WSGI is the runtime). Kept for
parity with `django-admin startproject` and future async migration."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

application = get_asgi_application()
