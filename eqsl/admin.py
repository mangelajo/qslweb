from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import QSO, CardTemplate, EmailQSL
from .render import RenderValidationError, validate_render_code


class CardTemplateAdminForm(forms.ModelForm):
    """Custom form for CardTemplate with python_render_code validation."""

    class Meta:
        model = CardTemplate
        fields = [
            "name",
            "description",
            "image",
            "language",
            "html_template",
            "python_render_code",
            "is_active",
        ]
        widgets = {
            "html_template": forms.Textarea(attrs={"rows": 10, "cols": 80, "class": "vLargeTextField"}),
            "python_render_code": forms.Textarea(
                attrs={
                    "rows": 20,
                    "cols": 100,
                    "class": "vLargeTextField",
                    "style": "font-family: monospace;",
                }
            ),
        }

    def clean_python_render_code(self):
        """Validate the python render code before saving."""
        render_code = self.cleaned_data.get("python_render_code", "")

        # If code is empty, that's fine (optional field)
        if not render_code.strip():
            return render_code

        # Validate the render code
        try:
            validate_render_code(render_code)
        except RenderValidationError as e:
            raise ValidationError(f"Invalid render code: {e}") from e

        return render_code


@admin.register(CardTemplate)
class CardTemplateAdmin(admin.ModelAdmin):
    form = CardTemplateAdminForm
    list_display = ["name", "language", "is_active", "has_render_code", "image_preview", "created_at", "updated_at"]
    list_filter = ["is_active", "language", "created_at"]
    search_fields = ["name", "description"]
    list_per_page = 25
    readonly_fields = ["created_at", "updated_at", "image_preview"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("name", "description", "language", "is_active")}),
        ("Card Design", {"fields": ("image", "image_preview")}),
        ("Email Template", {"fields": ("html_template",), "classes": ("wide",)}),
        (
            "Python Render Code",
            {
                "fields": ("python_render_code",),
                "classes": ("wide",),
                "description": (
                    "Optional Python code to dynamically render QSL card images. "
                    "Must define a render(card_template, qso) function that returns a PIL Image. "
                    "Code is executed in a sandboxed environment with 10-second timeout and 200MB memory limit."
                ),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Preview")
    def image_preview(self, obj):
        """Display a preview of the card template image."""
        if obj.image:
            from django.utils.html import format_html

            return format_html('<img src="{}" style="max-height: 100px; max-width: 200px;" />', obj.image.url)
        return "No image"

    @admin.display(boolean=True, description="Has Render Code")
    def has_render_code(self, obj):
        """Display whether the template has custom render code."""
        return bool(obj.python_render_code and obj.python_render_code.strip())


@admin.register(QSO)
class QSOAdmin(admin.ModelAdmin):
    # List display configuration
    list_display = [
        "timestamp",
        "call",
        "name",
        "band",
        "mode",
        "frequency",
        "rst_sent",
        "rst_rcvd",
        "my_call",
        "country",
        "has_email",
    ]
    list_filter = [
        "band",
        "mode",
        "timestamp",
        "country",
        "my_call",
    ]
    search_fields = [
        "call",
        "name",
        "my_call",
        "email",
        "country",
        "my_gridsquare",
        "sota_ref",
        "pota_ref",
    ]

    # Pagination
    list_per_page = 50
    list_max_show_all = 500

    # Date hierarchy for easy filtering by date
    date_hierarchy = "timestamp"

    # Ordering
    ordering = ["-timestamp"]

    # Readonly fields
    readonly_fields = ["created_at", "updated_at"]

    # Fieldsets for detail view
    fieldsets = (
        ("Station Information", {"fields": ("my_call", "my_gridsquare", "my_rig")}),
        ("Contact Information", {"fields": ("call", "name", "email", "country")}),
        ("QSO Details", {"fields": ("frequency", "band", "mode", "rst_sent", "rst_rcvd", "tx_pwr", "timestamp")}),
        ("References", {"fields": ("sota_ref", "pota_ref", "lang"), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    # Admin actions
    actions = ["export_selected_qsos"]

    @admin.action(description="Export selected QSOs as CSV")
    def export_selected_qsos(self, request, queryset):
        """Export selected QSOs to CSV format."""
        import csv

        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="qsos.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Timestamp",
                "Call",
                "Name",
                "Email",
                "Band",
                "Mode",
                "Frequency",
                "RST Sent",
                "RST Rcvd",
                "TX Power",
                "My Call",
                "My Grid",
                "My Rig",
                "Country",
                "SOTA Ref",
                "POTA Ref",
                "Language",
            ]
        )

        for qso in queryset:
            writer.writerow(
                [
                    qso.timestamp,
                    qso.call,
                    qso.name,
                    qso.email,
                    qso.band,
                    qso.mode,
                    qso.frequency,
                    qso.rst_sent,
                    qso.rst_rcvd,
                    qso.tx_pwr,
                    qso.my_call,
                    qso.my_gridsquare,
                    qso.my_rig,
                    qso.country,
                    qso.sota_ref,
                    qso.pota_ref,
                    qso.lang,
                ]
            )

        self.message_user(request, f"{queryset.count()} QSOs exported successfully.")
        return response

    # Custom display methods
    @admin.display(boolean=True, description="Has Email")
    def has_email(self, obj):
        """Display whether the QSO has an email address."""
        return bool(obj.email)


@admin.register(EmailQSL)
class EmailQSLAdmin(admin.ModelAdmin):
    """Admin interface for EmailQSL records."""

    list_display = [
        "sent_at",
        "qso_callsign",
        "recipient_email",
        "card_template",
        "delivery_status",
        "subject",
    ]
    list_filter = [
        "delivery_status",
        "sent_at",
        "card_template",
    ]
    search_fields = [
        "recipient_email",
        "sender_email",
        "subject",
        "body",
        "qso__call",
    ]

    # Pagination
    list_per_page = 50

    # Date hierarchy for easy filtering by date
    date_hierarchy = "sent_at"

    # Ordering
    ordering = ["-sent_at"]

    # Make most fields readonly since we don't want to edit sent emails
    readonly_fields = [
        "qso",
        "card_template",
        "sent_at",
        "recipient_email",
        "sender_email",
        "subject",
        "body",
        "delivery_status",
        "created_at",
        "updated_at",
    ]

    # Fieldsets for detail view
    fieldsets = (
        ("QSO Information", {"fields": ("qso", "card_template")}),
        ("Email Details", {"fields": ("sent_at", "recipient_email", "sender_email", "subject")}),
        ("Email Content", {"fields": ("body",), "classes": ("wide",)}),
        ("Status", {"fields": ("delivery_status",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    # Custom display methods
    @admin.display(description="Callsign", ordering="qso__call")
    def qso_callsign(self, obj):
        """Display the callsign from the related QSO."""
        return obj.qso.call

    def has_add_permission(self, _request):
        """Disable manual creation of EmailQSL records through admin."""
        return False

    def has_delete_permission(self, _request, obj=None):  # noqa: ARG002
        """Allow deletion for cleanup purposes."""
        return True
