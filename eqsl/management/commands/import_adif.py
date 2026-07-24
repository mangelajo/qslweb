"""
Management command to import QSOs from an ADIF file.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from eqsl.services import ADIFImportError, import_adif_content


class Command(BaseCommand):
    """Import QSOs from an ADIF file."""

    help = "Import QSOs from an ADIF file"

    def add_arguments(self, parser):
        parser.add_argument("adif_file", type=str, help="Path to the ADIF file")
        parser.add_argument(
            "--my-call",
            type=str,
            default="",
            help="Callsign to use for records without OPERATOR/STATION_CALLSIGN",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate import without saving to database",
        )

    def handle(self, **options):
        path = Path(options["adif_file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be saved"))

        try:
            summary = import_adif_content(
                path.read_text(errors="replace"),
                default_my_call=options["my_call"],
                dry_run=options["dry_run"],
            )
        except ADIFImportError as e:
            raise CommandError(str(e)) from e

        self.stdout.write(self.style.SUCCESS(f"Records in file: {summary['total']}"))
        self.stdout.write(self.style.SUCCESS(f"  Imported: {summary['imported']}"))
        self.stdout.write(self.style.WARNING(f"  Skipped (duplicates): {summary['skipped']}"))
        for error in summary["errors"]:
            self.stdout.write(self.style.ERROR(f"  Error: {error}"))
