"""
External API integration services.

This package provides clients for various amateur radio APIs:
- QRZ.com XML Data API (callsign lookups)
- QRZ.com Logbook API (QSO import/export)
"""

from .importer import ADIFImportError, import_adif_content, import_qso_dict, map_adif_record
from .mailer import EQSLSendError, compose_eqsl, language_for_qso, send_eqsl
from .qrz import QRZAPI, QRZAPIError, QRZSession
from .qrzlogbook import QRZLogbookAPI, QRZLogbookAPIError

__all__ = [
    "QRZAPI",
    "QRZAPIError",
    "QRZSession",
    "QRZLogbookAPI",
    "QRZLogbookAPIError",
    "EQSLSendError",
    "compose_eqsl",
    "language_for_qso",
    "send_eqsl",
    "ADIFImportError",
    "import_adif_content",
    "import_qso_dict",
    "map_adif_record",
]
