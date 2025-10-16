#!/usr/bin/env python
"""
Example script demonstrating QRZ XML Data API usage.

This script shows how to look up callsign information using the QRZ XML API.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qslweb.settings")

import django

django.setup()

from eqsl.services import QRZAPI, QRZAPIError  # noqa: E402


def lookup_callsign(callsign: str):
    """Look up and display callsign information."""
    try:
        # Initialize API (uses credentials from settings/environment)
        api = QRZAPI()

        print(f"\nLooking up: {callsign}")
        print("=" * 60)

        # Perform lookup
        data = api.lookup(callsign)

        # Display basic information
        print(f"\nCallsign: {data.get('call', 'N/A')}")
        print(f"Name: {data.get('fname', '')} {data.get('name', '')}")

        # Location
        if data.get("addr1") or data.get("addr2"):
            print("\nAddress:")
            if data.get("addr1"):
                print(f"  {data['addr1']}")
            if data.get("addr2"):
                print(f"  {data['addr2']}")
            location_parts = []
            if data.get("state"):
                location_parts.append(data["state"])
            if data.get("zip"):
                location_parts.append(data["zip"])
            if location_parts:
                print(f"  {', '.join(location_parts)}")
        if data.get("country"):
            print(f"Country: {data['country']}")

        # Coordinates
        if data.get("lat") and data.get("lon"):
            print(f"\nCoordinates: {data['lat']}, {data['lon']}")
        if data.get("grid"):
            print(f"Grid Square: {data['grid']}")

        # License info
        if data.get("class"):
            print(f"\nLicense Class: {data['class']}")

        # Contact methods
        if data.get("email"):
            print(f"\nEmail: {data['email']}")
        if data.get("url"):
            print(f"Website: {data['url']}")

        # QSL preferences
        qsl_methods = []
        if data.get("eqsl") == "1":
            qsl_methods.append("eQSL")
        if data.get("mqsl") == "1":
            qsl_methods.append("Mail")
        if data.get("lotw") == "1":
            qsl_methods.append("LoTW")
        if qsl_methods:
            print(f"\nQSL Methods: {', '.join(qsl_methods)}")

        # Biography
        if data.get("bio"):
            print(f"\nBio: {data['bio']} bytes available")

        # Session info
        print("\n" + "=" * 60)
        session_info = api.get_session_info()
        print(f"Lookups today: {session_info.get('count', 'N/A')}")
        if session_info.get("subexp"):
            print(f"Subscription expires: {session_info['subexp']}")

    except QRZAPIError as e:
        print(f"\nError: {e}")
        return False

    return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python qrz_lookup.py CALLSIGN [CALLSIGN...]")
        print("\nExample:")
        print("  python qrz_lookup.py W1AW")
        print("  python qrz_lookup.py W1AW K2XYZ N3ABC")
        sys.exit(1)

    # Look up each callsign provided
    for callsign in sys.argv[1:]:
        lookup_callsign(callsign.upper())
        print()


if __name__ == "__main__":
    main()
