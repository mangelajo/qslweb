# Seed default email templates (ported from the legacy CLI tool's mail_templates)

from django.db import migrations

CARD_IMG = '<p><img src="cid:{{ cid }}" alt="eQSL card" style="max-width: 100%;"></p>'

DEFAULT_SUBJECT = "Digital QSL from {{ qso.my_call }} to {{ qso.call }}"

ENGLISH_BODY = f"""<p>Hello {{{{ qso.name|default:"Dear OM" }}}}, and thank you for our QSO!</p>
{CARD_IMG}
<table>
  <tr><td>Frequency:</td><td>{{{{ qso.frequency }}}} MHz</td></tr>
  <tr><td>Band:</td><td>{{{{ qso.band }}}}</td></tr>
  <tr><td>Mode:</td><td>{{{{ qso.mode }}}}</td></tr>
  <tr><td>RST sent:</td><td>{{{{ qso.rst_sent }}}}</td></tr>
  <tr><td>RST received:</td><td>{{{{ qso.rst_rcvd }}}}</td></tr>
  <tr><td>Date:</td><td>{{{{ qso_date }}}}</td></tr>
</table>
<p>Our contact has also been confirmed on eQSL, QRZ and LOTW.</p>
<p>I am looking forward to our next QSO.</p>
<p>73 de {{{{ qso.my_call }}}}</p>
"""

SPANISH_BODY = f"""<p>Hola {{{{ qso.name|default:qso.call }}}}, ¡gracias por tu QSO!</p>
{CARD_IMG}
<table>
  <tr><td>Frecuencia:</td><td>{{{{ qso.frequency }}}} MHz</td></tr>
  <tr><td>Banda:</td><td>{{{{ qso.band }}}}</td></tr>
  <tr><td>Modo:</td><td>{{{{ qso.mode }}}}</td></tr>
  <tr><td>RST enviado:</td><td>{{{{ qso.rst_sent }}}}</td></tr>
  <tr><td>RST recibido:</td><td>{{{{ qso.rst_rcvd }}}}</td></tr>
  <tr><td>Fecha:</td><td>{{{{ qso_date }}}}</td></tr>
</table>
<p>Nuestro contacto {{{{ qso.mode }}}} está confirmado en LOTW, QRZ y eQSL.</p>
<p>Esperando nuestro próximo contacto.</p>
<p>73 de {{{{ qso.my_call }}}}</p>
"""

FRENCH_BODY = f"""<p>Bonjour {{{{ qso.name|default:qso.call }}}}, et merci pour le QSO!</p>
{CARD_IMG}
<table>
  <tr><td>Fréquence:</td><td>{{{{ qso.frequency }}}} MHz</td></tr>
  <tr><td>Bande:</td><td>{{{{ qso.band }}}}</td></tr>
  <tr><td>Mode:</td><td>{{{{ qso.mode }}}}</td></tr>
  <tr><td>RST envoyé:</td><td>{{{{ qso.rst_sent }}}}</td></tr>
  <tr><td>RST reçu:</td><td>{{{{ qso.rst_rcvd }}}}</td></tr>
  <tr><td>Date:</td><td>{{{{ qso_date }}}}</td></tr>
</table>
<p>Notre contact {{{{ qso.mode }}}} a été confirmé sur LOTW, eQSL et QRZ.</p>
<p>J'espère avoir le plaisir de vous recontacter très bientôt.</p>
<p>73 de {{{{ qso.my_call }}}}</p>
"""

TEMPLATES = [
    ("default", "en", ENGLISH_BODY),
    ("default-spanish", "es", SPANISH_BODY),
    ("default-french", "fr", FRENCH_BODY),
]


def populate_email_templates(apps, schema_editor):
    """Create default email templates for each supported language."""
    EmailTemplate = apps.get_model("eqsl", "EmailTemplate")
    for name, language, body in TEMPLATES:
        EmailTemplate.objects.create(
            name=name,
            language=language,
            subject=DEFAULT_SUBJECT,
            body=body,
            is_active=True,
            is_default=True,
        )


def reverse_populate_email_templates(apps, schema_editor):
    """Reverse migration - delete the seeded templates."""
    EmailTemplate = apps.get_model("eqsl", "EmailTemplate")
    EmailTemplate.objects.filter(name__in=[name for name, _, _ in TEMPLATES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("eqsl", "0009_emailqsl_error_message_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_email_templates, reverse_populate_email_templates),
    ]
