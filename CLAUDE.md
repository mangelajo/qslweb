# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QSL Web is a Django application for managing eQSL (electronic QSL) card confirmations via email for amateur radio operators. The application handles QSO (contact) records, generates personalized QSL card images, and integrates with QRZ.com for data synchronization.

## Technology Stack

- **Framework**: Django 5.1+
- **Python**: 3.12+
- **Package Manager**: uv
- **Database**: PostgreSQL (production), SQLite (development)
- **Background Tasks**: django-q2 with Redis
- **Image Processing**: Pillow
- **Testing**: pytest with pytest-django and playwright for UI tests
- **Linting**: ruff

## Development Commands

### Setup and Installation
```bash
# Install dependencies (includes dev dependencies)
uv sync

# Setup database
make migrate

# Create superuser
make createsuperuser
```

### Running the Application
```bash
# Start development server
make server

# Start with docker-compose (includes Redis, PostgreSQL)
make compose-up
```

### Testing
```bash
# Run all tests
make test
pytest

# Run with coverage
make test-coverage
pytest --cov

# Run only unit tests (skip slow/UI tests)
pytest -m "not slow and not ui"

# Run UI tests with playwright
pytest -m ui

# Run specific test file
pytest tests/test_qso.py

# Run tests in parallel
pytest -n auto
```

### Code Quality
```bash
# Lint code with ruff
make lint
ruff check .

# Auto-fix linting issues
make lint-fix
ruff check --fix .

# Format code
ruff format .
```

### Database Migrations
```bash
# Create migrations
make migrations
python manage.py makemigrations

# Apply migrations
make migrate
python manage.py migrate

# Show migration status
python manage.py showmigrations
```

### Background Tasks
```bash
# Start django-q2 cluster for background tasks
python manage.py qcluster
```

### QRZ.com Import
```bash
# Import QSOs from QRZ.com Logbook
python manage.py import_qsos

# Import with specific options
python manage.py import_qsos --option=ALL          # Fetch all QSOs
python manage.py import_qsos --option=MODIFIED     # Fetch recently modified (default)
python manage.py import_qsos --option=RANGE:start:end  # Fetch date range

# Import from specific logbook ID
python manage.py import_qsos --bookid=438677

# Dry run to preview without saving
python manage.py import_qsos --dry-run

# Use custom API key
python manage.py import_qsos --api-key=YOUR_KEY

# Combine parameters
python manage.py import_qsos --bookid=438677 --option=ALL --dry-run
```

## Architecture

### Core Components

1. **QSL Card Management**
   - Models for QSL card designs and templates
   - Image generation using Pillow for personalized eQSL cards
   - Support for multiple card designs with customizable colors, fonts, and signatures

2. **QSO Tracking**
   - ADIF-compatible data model for amateur radio contacts
   - Full support for standard ADIF fields (frequency, mode, RST, etc.)
   - QSL status tracking across multiple platforms (eQSL, paper, LoTW, QRZ)

3. **QRZ.com Integration**
   - API client for QRZ.com Logbook API (located in `eqsl/services.py`)
   - Import QSOs from QRZ.com using management command
   - Automatic duplicate detection based on call, timestamp, and band
   - Supports multiple fetch options (ALL, MODIFIED, RANGE)
   - Handles URL-encoded ADIF format with HTML entity decoding
   - The API returns data like `RESULT=OK&COUNT=143&ADIF=&lt;field:length&gt;value`
   - Parser decodes HTML entities and extracts ADIF fields

4. **Email System**
   - SMTP integration for sending eQSL cards
   - Template-based email generation
   - Batch sending capabilities with status tracking

### Django Apps Structure

The codebase should be organized into Django apps:
- `cards/` - QSL card design and image generation
- `qso/` - QSO record management
- `eqsl/` - eQSL sending and tracking
- `qrz/` - QRZ.com API integration
- `accounts/` - User authentication and profiles

### Background Tasks

Use django-q2 for:
- QRZ.com data synchronization
- Batch eQSL sending
- Email delivery monitoring
- Image generation for bulk operations

Tasks should be defined in `tasks.py` files within each app and scheduled using the Django admin interface.

### Image Processing

QSL card generation workflow:
1. Load card template image with Pillow
2. Overlay QSO details (callsign, date, frequency, mode, RST)
3. Add signature and customizations
4. Save as PNG/JPEG for email attachment
5. Cache generated images when possible

## Configuration

### Environment Variables

Required in `.env` file:
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (True/False)
- `DATABASE_URL` - Database connection string
- `REDIS_URL` - Redis connection for django-q2
- `QRZ_API_KEY`, `QRZ_USERNAME`, `QRZ_PASSWORD` - QRZ.com credentials
- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` - Email settings

### Testing Configuration

- Use `pytest.ini_options` in pyproject.toml for test configuration
- Playwright tests marked with `@pytest.mark.ui`
- Integration tests marked with `@pytest.mark.integration`
- Slow tests marked with `@pytest.mark.slow`

### Code Style

- Line length: 120 characters
- Follow Django conventions for models, views, and templates
- Use ruff for linting and formatting (configured in pyproject.toml)
- Type hints encouraged but not required

## Key Development Patterns

### Models
- Use Django's built-in fields for ADIF data types
- Add `created_at` and `updated_at` timestamps to all models
- Implement `__str__` methods for admin interface clarity

### Views
- Use class-based views (CBVs) for CRUD operations
- Add permission checks for user-specific data
- Use Django's pagination for large querysets

### Background Tasks
- Define tasks in `tasks.py` with `@async_task` decorator
- Handle errors gracefully and log failures
- Use task result tracking for monitoring

### Testing
- Write unit tests for models, forms, and utilities
- Use pytest fixtures for test data setup
- Mock external API calls (QRZ.com, SMTP)
  - QRZ API mock responses are in `tests/fixtures/qrz_responses.py`
  - These responses are based on real API output with anonymized personal data
  - QRZ returns URL-encoded ADIF format with HTML entities (`&lt;` and `&gt;`)
- Use playwright for end-to-end UI testing of critical flows
- Add `@pytest.fixture(autouse=True)` to clear test data between tests when needed
