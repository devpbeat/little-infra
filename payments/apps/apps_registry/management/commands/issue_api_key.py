from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from apps.apps_registry.models import (
    ApiKey,
    ConsumingApp,
    _generate_key_prefix,
    _generate_key_secret,
)


class Command(BaseCommand):
    help = "Issue a new API key for a ConsumingApp. Prints the raw secret exactly once."

    def add_arguments(self, parser):
        parser.add_argument("app_name", type=str, help="Name of the ConsumingApp to issue a key for.")

    def handle(self, *args, **options):
        app_name = options["app_name"]
        try:
            app = ConsumingApp.objects.get(name=app_name)
        except ConsumingApp.DoesNotExist as exc:
            raise CommandError(f"No ConsumingApp named '{app_name}'. Create it first.") from exc

        prefix = _generate_key_prefix()
        secret = _generate_key_secret()
        ApiKey.objects.create(app=app, prefix=prefix, hashed_secret=make_password(secret))

        raw_key = f"{prefix}.{secret}"
        self.stdout.write(self.style.SUCCESS("API key issued. Store this now — it will not be shown again:"))
        self.stdout.write(raw_key)
