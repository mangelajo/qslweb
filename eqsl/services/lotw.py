"""
LoTW (ARRL Logbook of The World) report download.

LoTW exposes the user's QSO/QSL records as an ADIF report; records are
imported through the shared ADIF import path.
"""

import logging

import requests

logger = logging.getLogger(__name__)

LOTW_REPORT_URL = "https://lotw.arrl.org/lotwuser/lotwreport.adi"


class LOTWAPIError(Exception):
    """Exception raised for LoTW download errors."""

    pass


def fetch_lotw_adif(username=None, password=None, since=None, qsl_only=False, timeout=120):
    """
    Download the LoTW ADIF report.

    Args:
        username: LoTW username (defaults to SendingSettings/env)
        password: LoTW password (defaults to SendingSettings/env)
        since: date/datetime; only QSOs received by LoTW after this date
        qsl_only: If True, fetch only confirmed QSLs instead of all QSOs
        timeout: HTTP timeout in seconds (the report can be slow)

    Returns:
        str: ADIF file content

    Raises:
        LOTWAPIError: On missing credentials, auth failure, or network error
    """
    if not username or not password:
        from eqsl.models import SendingSettings

        creds = SendingSettings.get_settings().effective_lotw()
        username = username or creds["username"]
        password = password or creds["password"]

    if not username or not password:
        raise LOTWAPIError("LoTW credentials not configured — set them on the Settings page or in .env")

    params = {
        "login": username,
        "password": password,
        "qso_query": "1",
        "qso_qsl": "yes" if qsl_only else "no",
    }
    if since:
        params["qso_qsorxsince"] = since.strftime("%Y-%m-%d")

    try:
        response = requests.get(LOTW_REPORT_URL, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        raise LOTWAPIError(f"Failed to download LoTW report: {e}") from e

    content = response.text
    # LoTW returns an HTML page (not ADIF) when the login is rejected
    if "<eoh>" not in content.lower():
        if "password" in content.lower() or "<html" in content.lower():
            raise LOTWAPIError("LoTW rejected the username/password")
        raise LOTWAPIError("LoTW returned an unexpected response (no ADIF header)")

    logger.info(f"Downloaded LoTW report: {len(content)} bytes")
    return content
