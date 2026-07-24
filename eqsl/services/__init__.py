"""
External API integration services.

This package provides clients for various amateur radio APIs:
- QRZ.com XML Data API (callsign lookups)
- QRZ.com Logbook API (QSO import/export)
"""

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
]
