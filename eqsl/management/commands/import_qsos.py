"""
Management command to import QSOs from QRZ.com Logbook.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from eqsl.models import QSO
from eqsl.services import QRZAPIError, QRZLogbookAPI


class Command(BaseCommand):
    """Import QSOs from QRZ.com Logbook API."""

    help = "Import QSOs from QRZ.com Logbook API"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--option",
            type=str,
            default="MODIFIED",
            help='Fetch option: "ALL", "MODIFIED", or "RANGE:start:end" (default: MODIFIED)',
        )
        parser.add_argument(
            "--api-key",
            type=str,
            help="QRZ API key (overrides settings)",
        )
        parser.add_argument(
            "--bookid",
            type=str,
            help="QRZ Logbook ID to sync from",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate import without saving to database",
        )

    def handle(self, **options):
        """Execute the command."""
        option = options["option"]
        api_key = options.get("api_key")
        bookid = options.get("bookid")
        dry_run = options["dry_run"]

        message = f"Starting QSO import from QRZ.com (option: {option}"
        if bookid:
            message += f", bookid: {bookid}"
        message += ")..."
        self.stdout.write(self.style.SUCCESS(message))

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be saved"))

        try:
            # Initialize QRZ API client
            api = QRZLogbookAPI(api_key=api_key)

            # Fetch QSOs from QRZ
            self.stdout.write("Fetching QSOs from QRZ.com...")
            qrz_qsos = api.fetch_qsos(option=option, bookid=bookid)
            self.stdout.write(self.style.SUCCESS(f"Fetched {len(qrz_qsos)} QSOs from QRZ.com"))

            if not qrz_qsos:
                self.stdout.write(self.style.WARNING("No QSOs to import"))
                return

            # Import QSOs
            imported_count = 0
            skipped_count = 0
            error_count = 0

            for qrz_qso in qrz_qsos:
                try:
                    result = self._import_qso(api, qrz_qso, dry_run)
                    if result == "imported":
                        imported_count += 1
                    elif result == "skipped":
                        skipped_count += 1
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f"Error importing QSO: {e}"))

            # Summary
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(self.style.SUCCESS("Import Summary:"))
            self.stdout.write(f"  Total fetched: {len(qrz_qsos)}")
            self.stdout.write(self.style.SUCCESS(f"  Imported: {imported_count}"))
            self.stdout.write(self.style.WARNING(f"  Skipped (duplicates): {skipped_count}"))
            if error_count > 0:
                self.stdout.write(self.style.ERROR(f"  Errors: {error_count}"))
            self.stdout.write("=" * 50)

        except QRZAPIError as e:
            self.stdout.write(self.style.ERROR(f"QRZ API Error: {e}"))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unexpected error: {e}"))
            raise

    def _import_qso(self, api: QRZLogbookAPI, qrz_qso: dict, dry_run: bool) -> str:
        """
        Import a single QSO.

        Returns:
            "imported" if QSO was imported, "skipped" if it already exists
        """
        # Map QRZ data to our model
        qso_data = api.map_qso_to_model(qrz_qso)

        # Check if QSO already exists (match by call, timestamp, and band)
        existing = QSO.objects.filter(
            call=qso_data["call"], timestamp=qso_data["timestamp"], band=qso_data["band"]
        ).first()

        if existing:
            return "skipped"

        if dry_run:
            self.stdout.write(f"  Would import: {qso_data['call']} on {qso_data['band']} at {qso_data['timestamp']}")
            return "imported"

        # Create new QSO
        with transaction.atomic():
            QSO.objects.create(**qso_data)
            self.stdout.write(
                self.style.SUCCESS(f"  Imported: {qso_data['call']} on {qso_data['band']} at {qso_data['timestamp']}")
            )

        return "imported"
