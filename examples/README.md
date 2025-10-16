# QSL Web Examples

This directory contains example scripts demonstrating various features of the QSL Web application.

## QRZ API Examples

### `qrz_lookup.py`

Demonstrates the QRZ XML Data API for callsign lookups.

**Usage:**
```bash
uv run python examples/qrz_lookup.py CALLSIGN [CALLSIGN...]
```

**Example:**
```bash
uv run python examples/qrz_lookup.py W1AW
```

**Requirements:**
- QRZ_USERNAME and QRZ_PASSWORD must be set in your `.env` file
- Active QRZ.com subscription for full data access

**Features:**
- Looks up callsign information
- Displays name, location, coordinates, grid square
- Shows license class and QSL preferences
- Displays current session information (lookup count, subscription expiry)

## Environment Setup

All examples require Django to be set up with proper environment variables in `.env`:

```bash
# Required for QRZ XML API
QRZ_USERNAME=your_username
QRZ_PASSWORD=your_password

# Required for QRZ Logbook API
QRZ_API_KEY=your_api_key
```
