"""
Shared QSO import logic and ADIF file parsing.

All import paths (QRZ Logbook API, ADIF files, future LoTW sync)
funnel through import_qso_dict() so duplicate detection stays in
one place.
"""

import logging
from datetime import UTC, datetime

import adif_io
from django.db import transaction

from eqsl.models import QSO

logger = logging.getLogger(__name__)


class ADIFImportError(Exception):
    """Exception raised when an ADIF file cannot be parsed."""

    pass


def import_qso_dict(qso_data, dry_run=False):
    """
    Create a QSO from mapped model data unless it already exists.

    Duplicates are matched on call + timestamp + band.

    Args:
        qso_data: Dict of QSO model fields (as from map_adif_record or
            QRZLogbookAPI.map_qso_to_model)
        dry_run: If True, only report what would happen

    Returns:
        str: "imported" or "skipped"
    """
    existing = QSO.objects.filter(call=qso_data["call"], timestamp=qso_data["timestamp"], band=qso_data["band"]).first()
    if existing:
        return "skipped"

    if not dry_run:
        with transaction.atomic():
            QSO.objects.create(**qso_data)
    return "imported"


def _adif_timestamp(record):
    """Parse an ADIF date/time pair into an aware datetime (UTC).

    Prefers the QSO start time (QSO_DATE/TIME_ON) to match the timestamps
    produced by the QRZ Logbook import, so duplicate detection works when
    the same log arrives via both paths.
    """
    date = record.get("QSO_DATE") or record.get("QSO_DATE_OFF")
    time = record.get("TIME_ON") or record.get("TIME_OFF") or "0000"
    if not date:
        raise KeyError("QSO_DATE")
    # ADIF times are HHMM or HHMMSS
    time = time.ljust(6, "0")[:6]
    naive = datetime.strptime(f"{date}{time}", "%Y%m%d%H%M%S")
    return naive.replace(tzinfo=UTC)


def map_adif_record(record, default_my_call=""):
    """
    Map a raw ADIF record dict (upper-case keys) to QSO model fields.

    Field fallbacks follow the legacy CLI tool: QSO_DATE_OFF/QSO_DATE,
    TIME_OFF/TIME_ON, RST defaults of 599, TX_PWR default 100.

    Args:
        record: ADIF record dict from adif_io
        default_my_call: Callsign to use when OPERATOR/STATION_CALLSIGN missing

    Raises:
        KeyError: If a required field (CALL, FREQ, BAND, MODE) is missing
    """
    return {
        "my_call": record.get("OPERATOR") or record.get("STATION_CALLSIGN") or default_my_call,
        "my_gridsquare": record.get("MY_GRIDSQUARE", ""),
        "my_rig": record.get("MY_RIG", ""),
        "call": record["CALL"],
        "name": record.get("NAME", ""),
        "email": record.get("EMAIL", ""),
        "frequency": float(record["FREQ"]),
        "band": record["BAND"],
        "mode": record["MODE"],
        "rst_sent": record.get("RST_SENT", "599"),
        "rst_rcvd": record.get("RST_RCVD", "599"),
        "tx_pwr": int(float(record.get("TX_PWR", 100))),
        "timestamp": _adif_timestamp(record),
        "sota_ref": record.get("SOTA_REF", ""),
        "pota_ref": record.get("POTA_REF", ""),
        "country": record.get("COUNTRY", ""),
        "lang": "en",
    }


def import_adif_content(content, default_my_call="", dry_run=False):
    """
    Import all QSO records from ADIF file content.

    Args:
        content: ADIF file content as a string
        default_my_call: Fallback my_call for records without OPERATOR
        dry_run: If True, parse and count without saving

    Returns:
        dict: {"total": int, "imported": int, "skipped": int, "errors": [str]}

    Raises:
        ADIFImportError: If the content cannot be parsed at all
    """
    try:
        records, _headers = adif_io.read_from_string(content)
    except Exception as e:
        raise ADIFImportError(f"Could not parse ADIF file: {e}") from e

    summary = {"total": len(records), "imported": 0, "skipped": 0, "errors": []}

    for index, record in enumerate(records, start=1):
        try:
            qso_data = map_adif_record(record, default_my_call=default_my_call)
            result = import_qso_dict(qso_data, dry_run=dry_run)
        except KeyError as e:
            summary["errors"].append(f"Record {index} ({record.get('CALL', '?')}): missing field {e}")
            continue
        except (ValueError, TypeError) as e:
            summary["errors"].append(f"Record {index} ({record.get('CALL', '?')}): {e}")
            continue
        summary[result] += 1

    logger.info(
        f"ADIF import{' (dry run)' if dry_run else ''}: "
        f"{summary['imported']} imported, {summary['skipped']} skipped, {len(summary['errors'])} errors"
    )
    return summary
