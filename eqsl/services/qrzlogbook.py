"""
QRZ.com Logbook API client.

This module provides access to the QRZ.com Logbook API for importing QSOs.
"""

import html
import re
import xml.etree.ElementTree as ET

import requests
from django.conf import settings


class QRZLogbookAPIError(Exception):
    """Exception raised for QRZ Logbook API errors."""

    pass


class QRZLogbookAPI:
    """Client for QRZ.com Logbook API."""

    BASE_URL = "https://logbook.qrz.com/api"

    def __init__(self, api_key: str | None = None):
        """Initialize QRZ Logbook API client."""
        self.api_key = api_key or settings.QRZ_API_KEY
        if not self.api_key:
            raise QRZLogbookAPIError("QRZ API key is required")

    def fetch_qsos(self, option: str = "MODIFIED", bookid: str | None = None) -> list[dict]:
        """
        Fetch QSOs from QRZ Logbook.

        Args:
            option: Fetch option - "ALL", "MODIFIED", "RANGE:start:end"
            bookid: Optional logbook ID to fetch from

        Returns:
            List of QSO dictionaries
        """
        url = f"{self.BASE_URL}"
        params = {"KEY": self.api_key, "ACTION": "FETCH", "OPTION": option}

        if bookid:
            params["BOOKID"] = bookid

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise QRZLogbookAPIError(f"Failed to fetch QSOs from QRZ: {e}") from e

        return self._parse_qsos(response.text)

    def _parse_qsos(self, response_data: str) -> list[dict]:
        """
        Parse QSO data from QRZ API response.

        Args:
            response_data: Response from QRZ API (can be URL-encoded or XML)

        Returns:
            List of QSO dictionaries
        """
        # Check if response is URL-encoded (ADIF format)
        if "=" in response_data and "&" in response_data and not response_data.strip().startswith("<"):
            return self._parse_adif_response(response_data)

        # Try to parse as XML
        try:
            root = ET.fromstring(response_data)
        except ET.ParseError as e:
            # Show first 200 characters of response for debugging
            preview = response_data[:200] if len(response_data) > 200 else response_data
            raise QRZLogbookAPIError(f"Failed to parse QRZ response: {e}\nResponse preview: {preview}") from e

        # Check for errors
        if root.tag == "QRZDatabase":
            error = root.find(".//ERROR")
            if error is not None:
                raise QRZLogbookAPIError(f"QRZ API Error: {error.text}")

        # Check result status
        result = root.find("RESULT")
        if result is not None:
            status = result.get("STATUS")
            if status == "FAIL":
                reason = result.get("REASON", "Unknown error")
                raise QRZLogbookAPIError(f"QRZ API returned FAIL: {reason}")

        # Parse QSO records
        qsos = []
        for qso_element in root.findall(".//QSO"):
            qso_data = {}
            for field in qso_element:
                qso_data[field.tag.lower()] = field.text

            qsos.append(qso_data)

        return qsos

    def _parse_adif_response(self, response_data: str) -> list[dict]:
        """
        Parse URL-encoded ADIF response from QRZ API.

        Args:
            response_data: URL-encoded response

        Returns:
            List of QSO dictionaries
        """
        # Manually parse response since ADIF data contains newlines
        # which parse_qs doesn't handle properly
        result = ""
        count = 0
        adif_data = ""

        # Extract RESULT
        if "RESULT=" in response_data:
            result_match = response_data.split("RESULT=")[1].split("&")[0]
            result = result_match

        # Extract COUNT
        if "COUNT=" in response_data:
            count_match = response_data.split("COUNT=")[1].split("&")[0]
            count = int(count_match)

        # Check for errors
        if result == "FAIL":
            # Try to get reason
            reason = "Unknown error"
            if "REASON=" in response_data:
                reason = response_data.split("REASON=")[1].split("&")[0]
            raise QRZLogbookAPIError(f"QRZ API returned FAIL: {reason}")

        if count == 0:
            return []

        # Extract ADIF data - everything after "ADIF="
        if "&ADIF=" in response_data:
            adif_data = response_data.split("&ADIF=", 1)[1]
        elif response_data.startswith("ADIF="):
            adif_data = response_data.split("ADIF=", 1)[1]

        if not adif_data:
            return []

        # Parse ADIF format (simplified parser)
        qsos = self._parse_adif(adif_data)
        return qsos

    def _parse_adif(self, adif_data: str) -> list[dict]:
        """
        Parse ADIF data format.

        Args:
            adif_data: ADIF formatted data

        Returns:
            List of QSO dictionaries
        """
        # Decode HTML entities (QRZ API returns &lt; and &gt; instead of < and >)
        adif_data = html.unescape(adif_data)

        qsos = []
        # Split by <eor> (end of record) marker
        records = adif_data.split("<eor>")

        for record in records:
            if not record.strip():
                continue

            qso_data = {}
            # Parse ADIF fields: <FIELD:length>value
            pattern = r"<(\w+):(\d+)>([^<]*)"
            matches = re.findall(pattern, record, re.IGNORECASE)

            for field_name, _length, value in matches:
                qso_data[field_name.lower()] = value.strip()

            if qso_data:
                qsos.append(qso_data)

        return qsos

    def map_qso_to_model(self, qrz_qso: dict) -> dict:
        """
        Map QRZ QSO data to our QSO model fields.

        Args:
            qrz_qso: QSO data from QRZ API

        Returns:
            Dictionary with mapped fields for QSO model
        """
        from django.utils import timezone
        from django.utils.dateparse import parse_datetime

        # Parse timestamp
        qso_date = qrz_qso.get("qso_date", "")
        qso_time = qrz_qso.get("time_on", "")
        timestamp_str = f"{qso_date} {qso_time}"
        timestamp = parse_datetime(timestamp_str.replace(" ", "T") + "Z") if qso_date and qso_time else timezone.now()

        return {
            "my_call": qrz_qso.get("station_callsign", ""),
            "my_gridsquare": qrz_qso.get("my_gridsquare", ""),
            "my_rig": qrz_qso.get("my_rig", ""),
            "call": qrz_qso.get("call", ""),
            "name": qrz_qso.get("name", ""),
            "email": qrz_qso.get("email", ""),
            "frequency": float(qrz_qso.get("freq", 0)) if qrz_qso.get("freq") else 0.0,
            "band": qrz_qso.get("band", ""),
            "mode": qrz_qso.get("mode", ""),
            "rst_sent": qrz_qso.get("rst_sent", ""),
            "rst_rcvd": qrz_qso.get("rst_rcvd", ""),
            "tx_pwr": int(qrz_qso.get("tx_pwr", 0)) if qrz_qso.get("tx_pwr") else 0,
            "timestamp": timestamp,
            "sota_ref": qrz_qso.get("sota_ref", ""),
            "pota_ref": qrz_qso.get("pota_ref", ""),
            "country": qrz_qso.get("country", ""),
            "lang": "en",
        }
