"""
QRZ.com XML Data API client.

This module provides access to the QRZ.com XML Data API for callsign lookups.
Specification: https://www.qrz.com/page/current_spec.html
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import requests
from django.conf import settings


class QRZAPIError(Exception):
    """Exception raised for QRZ XML API errors."""

    pass


class QRZSession:
    """
    QRZ XML API session manager.

    Handles authentication and session key caching.
    """

    BASE_URL = "https://xmldata.qrz.com/xml/current/"

    def __init__(self, username: str | None = None, password: str | None = None, agent: str = "qslweb/1.0"):
        """
        Initialize QRZ session.

        Args:
            username: QRZ username (defaults to settings.QRZ_USERNAME)
            password: QRZ password (defaults to settings.QRZ_PASSWORD)
            agent: User agent string to identify client software
        """
        self.username = username or settings.QRZ_USERNAME
        self.password = password or settings.QRZ_PASSWORD
        self.agent = agent

        if not self.username or not self.password:
            raise QRZAPIError("QRZ username and password are required")

        self._session_key: str | None = None
        self._session_expires: datetime | None = None
        self._session_info: dict = {}

    def get_session_key(self) -> str:
        """
        Get valid session key, authenticating if necessary.

        Returns:
            Session key string

        Raises:
            QRZAPIError: If authentication fails
        """
        # Check if we have a valid cached session
        if self._session_key and self._session_expires and datetime.now() < self._session_expires:
            return self._session_key

        # Authenticate and get new session key
        return self._authenticate()

    def _authenticate(self) -> str:
        """
        Authenticate with QRZ and get session key.

        Returns:
            Session key string

        Raises:
            QRZAPIError: If authentication fails
        """
        params = {"username": self.username, "password": self.password, "agent": self.agent}

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise QRZAPIError(f"Failed to connect to QRZ: {e}") from e

        # Parse XML response
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as e:
            raise QRZAPIError(f"Failed to parse QRZ response: {e}") from e

        # Handle XML namespace if present
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}")[0] + "}"

        # Check for errors
        error = root.find(f".//{namespace}Error")
        if error is not None:
            raise QRZAPIError(f"QRZ authentication error: {error.text}")

        # Extract session information
        session = root.find(f"{namespace}Session")
        if session is None:
            raise QRZAPIError("No session information in QRZ response")

        key_element = session.find(f"{namespace}Key")
        if key_element is None or not key_element.text:
            raise QRZAPIError("No session key in QRZ response")

        self._session_key = key_element.text

        # Cache session for 23 hours (sessions expire after 24 hours)
        self._session_expires = datetime.now() + timedelta(hours=23)

        # Store additional session info
        self._session_info = {}
        for child in session:
            if child.text:
                # Remove namespace from tag
                tag = child.tag.replace(namespace, "")
                self._session_info[tag.lower()] = child.text

        return self._session_key

    @property
    def session_info(self) -> dict:
        """Get session information (GMTime, Count, SubExp, etc.)."""
        return self._session_info


class QRZAPI:
    """
    QRZ XML Data API client for callsign lookups.

    Example:
        >>> api = QRZAPI()
        >>> callsign_data = api.lookup("W1AW")
        >>> print(callsign_data["name"])
    """

    def __init__(self, username: str | None = None, password: str | None = None, agent: str = "qslweb/1.0"):
        """
        Initialize QRZ API client.

        Args:
            username: QRZ username (defaults to settings.QRZ_USERNAME)
            password: QRZ password (defaults to settings.QRZ_PASSWORD)
            agent: User agent string to identify client software
        """
        self.session = QRZSession(username=username, password=password, agent=agent)

    def lookup(self, callsign: str) -> dict:
        """
        Look up callsign information.

        Args:
            callsign: Amateur radio callsign to look up

        Returns:
            Dictionary with callsign data

        Raises:
            QRZAPIError: If lookup fails or callsign not found
        """
        # Get valid session key
        session_key = self.session.get_session_key()

        # Make lookup request
        params = {"s": session_key, "callsign": callsign.upper()}

        try:
            response = requests.get(self.session.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise QRZAPIError(f"Failed to lookup callsign: {e}") from e

        # Parse XML response
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as e:
            raise QRZAPIError(f"Failed to parse QRZ response: {e}") from e

        # Handle XML namespace if present
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}")[0] + "}"

        # Check for errors
        error = root.find(f".//{namespace}Error")
        if error is not None:
            # Session might have expired, try re-authenticating once
            if "invalid session key" in error.text.lower() or "session timeout" in error.text.lower():
                self.session._session_key = None
                session_key = self.session.get_session_key()
                params["s"] = session_key
                # Retry request
                try:
                    response = requests.get(self.session.BASE_URL, params=params, timeout=30)
                    response.raise_for_status()
                    root = ET.fromstring(response.text)
                    # Re-extract namespace for retry
                    if root.tag.startswith("{"):
                        namespace = root.tag.split("}")[0] + "}"
                    error = root.find(f".//{namespace}Error")
                    if error is not None:
                        raise QRZAPIError(f"QRZ lookup error: {error.text}")
                except (requests.RequestException, ET.ParseError) as e:
                    raise QRZAPIError(f"Failed to retry lookup: {e}") from e
            else:
                raise QRZAPIError(f"QRZ lookup error: {error.text}")

        # Extract callsign data
        callsign_elem = root.find(f"{namespace}Callsign")
        if callsign_elem is None:
            raise QRZAPIError(f"No data found for callsign: {callsign}")

        # Convert XML to dictionary
        data = {}
        for child in callsign_elem:
            if child.text:
                # Remove namespace from tag
                tag = child.tag.replace(namespace, "")
                data[tag.lower()] = child.text

        return data

    def get_session_info(self) -> dict:
        """
        Get current session information.

        Returns:
            Dictionary with session info (GMTime, Count, SubExp, etc.)
        """
        # Ensure we have a valid session
        self.session.get_session_key()
        return self.session.session_info
