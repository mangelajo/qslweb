"""
Background-capable tasks for the eqsl app.

These functions are plain callables so they can run synchronously from
views today and be enqueued via django-q2's async_task later.
"""

import logging
from datetime import timedelta

from django.utils import timezone

from eqsl.models import QSO
from eqsl.services import QRZAPI, QRZAPIError

logger = logging.getLogger(__name__)

# Fields enrichment may fill on a QSO, mapped from QRZ lookup keys
ENRICHABLE_FIELDS = {
    "email": "email",
    "country": "country",
}


def _full_name(qrz_data):
    """Build a full name from QRZ fname/name fields."""
    return " ".join(part for part in (qrz_data.get("fname"), qrz_data.get("name")) if part).strip()


def enrich_qso(qso_id, api=None):
    """
    Fill blank contact fields (name, email, country) on a QSO from QRZ.com.

    Existing non-blank values are never overwritten. Stamps qrz_lookup_at
    even when nothing is found, so bulk enrichment can skip recent misses.

    Args:
        qso_id: Primary key of the QSO to enrich
        api: Optional QRZAPI instance (shared across bulk lookups)

    Returns:
        dict: {"call": str, "found": bool, "updated": [field names], "error": str | None}
    """
    qso = QSO.objects.get(pk=qso_id)
    result = {"call": qso.call, "found": False, "updated": [], "error": None}

    if api is None:
        api = QRZAPI()

    try:
        data = api.lookup(qso.call)
    except QRZAPIError as e:
        message = str(e)
        # QRZ reports misses as "Not found: <CALL>"; our client raises
        # "No data found for callsign" when the response has no data
        if "not found" in message.lower() or "no data found" in message.lower():
            # Callsign not in QRZ: record the miss so we don't retry hot
            qso.qrz_lookup_at = timezone.now()
            qso.save(update_fields=["qrz_lookup_at", "updated_at"])
            result["error"] = f"{qso.call} not found on QRZ.com"
            logger.info(f"QRZ lookup: no data for {qso.call}")
            return result
        # Auth/network errors should surface to the caller, not mark the QSO
        raise

    result["found"] = True
    update_fields = ["qrz_lookup_at", "updated_at"]

    if not qso.name:
        name = _full_name(data)
        if name:
            qso.name = name
            update_fields.append("name")
    for qso_field, qrz_key in ENRICHABLE_FIELDS.items():
        if not getattr(qso, qso_field) and data.get(qrz_key):
            setattr(qso, qso_field, data[qrz_key])
            update_fields.append(qso_field)

    qso.qrz_lookup_at = timezone.now()
    qso.save(update_fields=update_fields)

    result["updated"] = [f for f in update_fields if f not in ("qrz_lookup_at", "updated_at")]
    logger.info(f"QRZ lookup for {qso.call}: updated {result['updated'] or 'nothing'}")
    return result


def enrich_missing_emails(limit=None, retry_after_days=30):
    """
    Enrich all QSOs that have no email address.

    Skips QSOs already looked up within retry_after_days. Stops early on
    auth/network errors (they would fail for every lookup).

    Args:
        limit: Maximum number of QSOs to process (None for all)
        retry_after_days: Skip QSOs looked up more recently than this

    Returns:
        dict: {"processed": int, "emails_found": int, "not_found": int,
               "skipped_recent": int, "error": str | None}
    """
    cutoff = timezone.now() - timedelta(days=retry_after_days)
    candidates = QSO.objects.filter(email="")
    skipped_recent = candidates.filter(qrz_lookup_at__gte=cutoff).count()
    queryset = candidates.exclude(qrz_lookup_at__gte=cutoff).order_by("-timestamp")
    if limit:
        queryset = queryset[:limit]

    summary = {
        "processed": 0,
        "emails_found": 0,
        "not_found": 0,
        "skipped_recent": skipped_recent,
        "error": None,
    }

    api = QRZAPI()
    for qso in queryset:
        try:
            result = enrich_qso(qso.pk, api=api)
        except QRZAPIError as e:
            summary["error"] = str(e)
            logger.error(f"Bulk QRZ enrichment aborted: {e}")
            break
        summary["processed"] += 1
        if not result["found"]:
            summary["not_found"] += 1
        elif "email" in result["updated"]:
            summary["emails_found"] += 1

    return summary
