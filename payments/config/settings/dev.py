"""Development and test settings."""

from .base import *  # noqa: F401,F403

DEBUG = True

if not SECRET_KEY:  # noqa: F405
    SECRET_KEY = "dev-insecure-secret-key-do-not-use-in-production"  # noqa: F405

if not ALLOWED_HOSTS:  # noqa: F405
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]  # noqa: F405
