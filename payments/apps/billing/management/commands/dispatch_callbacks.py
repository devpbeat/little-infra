"""Retry sweep for outbound payment callbacks.

Run from cron (every minute is fine). The in-process thread started at
confirmation time handles the happy path; this command is what makes a
recycled worker or a consuming app that was down for an hour recoverable.
"""

from django.core.management.base import BaseCommand

from apps.billing.callbacks import dispatch_pending


class Command(BaseCommand):
    help = "Deliver pending outbound payment callbacks whose next attempt is due."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        delivered = dispatch_pending(limit=options["limit"])
        self.stdout.write(self.style.SUCCESS(f"Delivered {delivered} callback(s)."))
