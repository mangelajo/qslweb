"""
Tests for QRZ XML Data API.
"""

from unittest.mock import MagicMock, patch

import pytest

from eqsl.services import QRZAPI, QRZAPIError, QRZSession

# Sample XML responses
VALID_SESSION_XML = """<?xml version="1.0" encoding="utf-8" ?>
<QRZDatabase version="1.34">
    <Session>
        <Key>2331uf894c4bd29f3923f3bacf02c532d7bd9</Key>
        <Count>123</Count>
        <SubExp>Wed Jan 1 12:34:56 2025</SubExp>
        <GMTime>Sun Dec 25 12:34:56 2024</GMTime>
    </Session>
</QRZDatabase>
"""

SESSION_ERROR_XML = """<?xml version="1.0" encoding="utf-8" ?>
<QRZDatabase version="1.34">
    <Session>
        <Error>Username/password incorrect</Error>
    </Session>
</QRZDatabase>
"""

CALLSIGN_LOOKUP_XML = """<?xml version="1.0" encoding="utf-8" ?>
<QRZDatabase version="1.34">
    <Callsign>
        <call>W1AW</call>
        <fname>Hiram</fname>
        <name>Percy Maxim</name>
        <addr1>225 Main Street</addr1>
        <addr2>Newington</addr2>
        <state>CT</state>
        <zip>06111</zip>
        <country>United States</country>
        <lat>41.714775</lat>
        <lon>-72.727260</lon>
        <grid>FN31pr</grid>
        <county>Hartford</county>
        <class>CLUB</class>
        <email>w1aw@arrl.org</email>
        <url>http://www.arrl.org</url>
        <bio>Headquarters station of the American Radio Relay League</bio>
        <eqsl>1</eqsl>
        <mqsl>1</mqsl>
        <lotw>1</lotw>
    </Callsign>
    <Session>
        <Key>2331uf894c4bd29f3923f3bacf02c532d7bd9</Key>
        <Count>124</Count>
        <GMTime>Sun Dec 25 12:35:01 2024</GMTime>
    </Session>
</QRZDatabase>
"""

CALLSIGN_NOT_FOUND_XML = """<?xml version="1.0" encoding="utf-8" ?>
<QRZDatabase version="1.34">
    <Session>
        <Key>2331uf894c4bd29f3923f3bacf02c532d7bd9</Key>
        <Error>Not found: ZZ9ZZZ</Error>
    </Session>
</QRZDatabase>
"""

INVALID_SESSION_XML = """<?xml version="1.0" encoding="utf-8" ?>
<QRZDatabase version="1.34">
    <Session>
        <Error>Invalid session key</Error>
    </Session>
</QRZDatabase>
"""


class TestQRZSession:
    """Test QRZ session management."""

    def test_init_without_credentials(self):
        """Test initialization without credentials raises error."""
        with patch("eqsl.services.qrz.settings") as mock_settings:
            mock_settings.QRZ_USERNAME = None
            mock_settings.QRZ_PASSWORD = None
            with pytest.raises(QRZAPIError, match="username and password are required"):
                QRZSession()

    def test_init_with_credentials(self):
        """Test initialization with credentials."""
        session = QRZSession(username="test_user", password="test_pass")
        assert session.username == "test_user"
        assert session.password == "test_pass"
        assert session.agent == "qslweb/1.0"

    @patch("eqsl.services.qrz.requests.get")
    def test_authenticate_success(self, mock_get):
        """Test successful authentication."""
        mock_response = MagicMock()
        mock_response.text = VALID_SESSION_XML
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        session = QRZSession(username="test_user", password="test_pass")
        key = session.get_session_key()

        assert key == "2331uf894c4bd29f3923f3bacf02c532d7bd9"
        assert session.session_info["count"] == "123"
        assert "subexp" in session.session_info

    @patch("eqsl.services.qrz.requests.get")
    def test_authenticate_error(self, mock_get):
        """Test authentication with invalid credentials."""
        mock_response = MagicMock()
        mock_response.text = SESSION_ERROR_XML
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        session = QRZSession(username="bad_user", password="bad_pass")
        with pytest.raises(QRZAPIError, match="Username/password incorrect"):
            session.get_session_key()

    @patch("eqsl.services.qrz.requests.get")
    def test_session_key_caching(self, mock_get):
        """Test that session keys are cached and reused."""
        mock_response = MagicMock()
        mock_response.text = VALID_SESSION_XML
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        session = QRZSession(username="test_user", password="test_pass")

        # First call should authenticate
        key1 = session.get_session_key()
        assert mock_get.call_count == 1

        # Second call should use cached key
        key2 = session.get_session_key()
        assert mock_get.call_count == 1  # No additional call
        assert key1 == key2


class TestQRZAPI:
    """Test QRZ XML API client."""

    @patch("eqsl.services.qrz.requests.get")
    def test_lookup_success(self, mock_get):
        """Test successful callsign lookup."""
        # First request: authentication
        auth_response = MagicMock()
        auth_response.text = VALID_SESSION_XML
        auth_response.raise_for_status = MagicMock()

        # Second request: lookup
        lookup_response = MagicMock()
        lookup_response.text = CALLSIGN_LOOKUP_XML
        lookup_response.raise_for_status = MagicMock()

        mock_get.side_effect = [auth_response, lookup_response]

        api = QRZAPI(username="test_user", password="test_pass")
        data = api.lookup("W1AW")

        assert data["call"] == "W1AW"
        assert data["fname"] == "Hiram"
        assert data["name"] == "Percy Maxim"
        assert data["state"] == "CT"
        assert data["grid"] == "FN31pr"
        assert data["email"] == "w1aw@arrl.org"
        assert data["eqsl"] == "1"
        assert data["lotw"] == "1"

    @patch("eqsl.services.qrz.requests.get")
    def test_lookup_not_found(self, mock_get):
        """Test callsign lookup for non-existent callsign."""
        # First request: authentication
        auth_response = MagicMock()
        auth_response.text = VALID_SESSION_XML
        auth_response.raise_for_status = MagicMock()

        # Second request: lookup
        lookup_response = MagicMock()
        lookup_response.text = CALLSIGN_NOT_FOUND_XML
        lookup_response.raise_for_status = MagicMock()

        mock_get.side_effect = [auth_response, lookup_response]

        api = QRZAPI(username="test_user", password="test_pass")
        with pytest.raises(QRZAPIError, match="Not found"):
            api.lookup("ZZ9ZZZ")

    @patch("eqsl.services.qrz.requests.get")
    def test_lookup_session_expired_retry(self, mock_get):
        """Test that expired sessions are automatically refreshed."""
        # First request: authentication
        auth_response = MagicMock()
        auth_response.text = VALID_SESSION_XML
        auth_response.raise_for_status = MagicMock()

        # Second request: lookup with expired session
        expired_response = MagicMock()
        expired_response.text = INVALID_SESSION_XML
        expired_response.raise_for_status = MagicMock()

        # Third request: re-authentication
        reauth_response = MagicMock()
        reauth_response.text = VALID_SESSION_XML
        reauth_response.raise_for_status = MagicMock()

        # Fourth request: successful lookup
        lookup_response = MagicMock()
        lookup_response.text = CALLSIGN_LOOKUP_XML
        lookup_response.raise_for_status = MagicMock()

        mock_get.side_effect = [auth_response, expired_response, reauth_response, lookup_response]

        api = QRZAPI(username="test_user", password="test_pass")
        data = api.lookup("W1AW")

        assert data["call"] == "W1AW"
        assert mock_get.call_count == 4  # auth, failed lookup, reauth, successful lookup

    @patch("eqsl.services.qrz.requests.get")
    def test_get_session_info(self, mock_get):
        """Test retrieving session information."""
        mock_response = MagicMock()
        mock_response.text = VALID_SESSION_XML
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        api = QRZAPI(username="test_user", password="test_pass")
        info = api.get_session_info()

        assert info["count"] == "123"
        assert "subexp" in info
        assert "gmtime" in info

    @patch("eqsl.services.qrz.requests.get")
    def test_network_error(self, mock_get):
        """Test handling of network errors."""
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        api = QRZAPI(username="test_user", password="test_pass")
        with pytest.raises(QRZAPIError, match="Failed to connect to QRZ"):
            api.lookup("W1AW")
