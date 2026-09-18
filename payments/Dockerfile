# syntax=docker/dockerfile:1
FROM --platform=linux/arm64 python:3.12-slim-bookworm AS builder

RUN pip install --no-cache-dir uv

WORKDIR /build

COPY pyproject.toml .

RUN uv venv /opt/venv \
    && uv pip install --python /opt/venv/bin/python .

FROM --platform=linux/arm64 python:3.12-slim-bookworm AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY . .

RUN mkdir -p /app/staticfiles \
    && chmod +x /app/entrypoint.sh \
    && chown -R app:app /app

USER app

# Build-time-only values: collectstatic needs settings to load but never
# touches the database or real secrets.
RUN DJANGO_SECRET_KEY=build-time-only ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# --timeout 180: AI template generation/templatization holds a worker for
# 30-90s; the 30s default killed workers mid-stream (WORKER TIMEOUT). With
# 3 sync workers and admin-only, low-frequency AI actions, a long timeout
# is the pragmatic choice over async offloading at this scale.
CMD ["gunicorn", "config.wsgi:application", "--workers", "3", "--timeout", "180", "--bind", "0.0.0.0:8000"]
