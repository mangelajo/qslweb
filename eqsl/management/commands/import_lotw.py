"""
Management command to import QSOs from LoTW.
"""

from django.core.management.base import BaseCommand, CommandError

from eqsl.services import ADIFImportError, LOTWAPIError
from eqsl.tasks import sync_lotw


class Command(BaseCommand):
    """Import QSOs from ARRL Logbook of The World."""

    help = "Import QSOs from LoTW (incremental since last sync by default)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            help="Fetch the entire logbook instead of records since the last sync",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate import without saving to database",
        )

    def handle(self, **options):
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be saved"))

        self.stdout.write("Downloading LoTW report...")
        try:
            summary = sync_lotw(full=options["full"], dry_run=options["dry_run"])
        except (LOTWAPIError, ADIFImportError) as e:
            raise CommandError(str(e)) from e

        self.stdout.write(self.style.SUCCESS(f"Records in report: {summary['total']}"))
        self.stdout.write(self.style.SUCCESS(f"  Imported: {summary['imported']}"))
        self.stdout.write(self.style.WARNING(f"  Skipped (duplicates): {summary['skipped']}"))
        for error in summary["errors"]:
            self.stdout.write(self.style.ERROR(f"  Error: {error}"))
