# QSL Web

[![CI](https://github.com/mangelajo/qslweb/actions/workflows/ci.yml/badge.svg)](https://github.com/mangelajo/qslweb/actions/workflows/ci.yml)

A Django application for managing eQSL card confirmations via email. This application allows you to:

- Manage QSL card designs and templates
- Track QSO (contact) records with ADIF-compatible fields
- Send eQSL cards via email with generated images
- Integrate with QRZ.com for QSO data synchronization
- Track sent eQSLs and their status

## Features

### QSL Card Management
- Upload and manage QSL card template images
- Customize card appearance (colors, fonts, signatures)
- Support for multiple card designs

### QSO Tracking
- Store QSO records with full ADIF field support
- Import QSOs from QRZ.com logbook
- Track QSL status (sent/received) for various platforms
- Search and filter QSOs by various criteria

### eQSL Sending
- Generate personalized QSL card images
- Send eQSL cards via email
- Track sending status and delivery
- Support for multiple email templates and languages

### QRZ Integration
- Sync QSOs from QRZ.com logbook
- Lookup callsign information
- Manage QRZ API credentials securely

## Installation

### Prerequisites
- Python 3.12+
- PostgreSQL (for production) or SQLite (for development)
- Redis (for background tasks)

### Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd qslweb
```

2. Install dependencies:
```bash
uv sync
```

3. Create environment file:
```bash
cp env.example .env
# Edit .env with your settings
```

4. Run migrations:
```bash
make migrate
```

5. Create superuser:
```bash
make createsuperuser
```

6. Start development server:
```bash
make server
```

### Production Setup

1. Build and run with Docker Compose:
```bash
make compose-up
```

2. Or build container manually:
```bash
make container-build-prod
make container-run
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Django settings
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com

# Database
DATABASE_URL=postgres://user:password@localhost:5432/qslweb

# Redis
REDIS_URL=redis://localhost:6379/0

# QRZ API credentials
QRZ_API_KEY=your-qrz-api-key
QRZ_USERNAME=your-qrz-username
QRZ_PASSWORD=your-qrz-password

# SMTP settings for sending eQSL emails
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

### QRZ API Setup

1. Log in to QRZ.com
2. Go to Logbook → Settings → API Key
3. Generate an API key
4. Add your QRZ credentials to the admin panel or environment variables

## Usage

### Admin Interface

Access the admin interface at `/admin/` to:
- Manage QSL card designs
- Configure QRZ credentials
- Set up email templates
- View sync logs

### QSL Card Management

1. Go to QSL Cards section
2. Upload your QSL card template image
3. Configure colors, fonts, and signature text
4. Set as active for use in eQSL generation

### QSO Management

1. Add QSOs manually or sync from QRZ
2. Ensure QSOs have email addresses for eQSL sending
3. Use filters to find QSOs that need eQSLs

### Sending eQSLs

1. Go to eQSL section
2. Select QSOs that need eQSLs
3. Choose QSL card design and email template
4. Send individual eQSLs or batch send

## Development

### Running Tests

```bash
make test
make test-coverage
```

### Code Quality

```bash
make lint
make lint-fix
```

### Database Migrations

```bash
make migrations
make migrate
```

## API Integration

### QRZ.com Integration

The application integrates with QRZ.com using their Logbook API:

- **QSO Sync**: Import QSOs from your QRZ logbook
- **Callsign Lookup**: Get detailed information about callsigns
- **Email Lookup**: Automatically find email addresses for QSOs

### SMTP Configuration

Configure your SMTP settings to send eQSL emails. Popular providers:

- **Gmail**: Use App Passwords for authentication
- **Outlook**: Use OAuth2 or App Passwords
- **Custom SMTP**: Configure with your provider's settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the admin interface help text
