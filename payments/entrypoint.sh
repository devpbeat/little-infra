#!/bin/sh
set -e

python manage.py migrate --noinput

# Create the admin user on first boot when credentials are provided.
# createsuperuser --noinput reads DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD
# and fails if the user already exists, so tolerate that case.
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    python manage.py createsuperuser --noinput 2>/dev/null || true
fi

exec "$@"
