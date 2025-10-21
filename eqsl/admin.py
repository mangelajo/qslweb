from codemirror2.widgets import CodeMirrorEditor
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import QSO, CardTemplate, EmailQSL, RenderTemplate
from .render import RenderValidationError, validate_render_code


class CardTemplateAdminForm(forms.ModelForm):
    """Custom form for CardTemplate."""

    class Meta:
        model = CardTemplate
        fields = [
            "name",
            "description",
            "image",
            "language",
            "html_template",
            "render_template",
            "is_active",
        ]
        widgets = {
            "html_template": forms.Textarea(
                attrs={
                    "rows": 10,
                    "class": "vLargeTextField",
                    "style": "width: 100%;",
                }
            ),
        }


class RenderTemplateAdminForm(forms.ModelForm):
    """Custom form for RenderTemplate with python_render_code validation."""

    class Meta:
        model = RenderTemplate
        fields = ["name", "description", "python_render_code"]
        widgets = {
            "python_render_code": CodeMirrorEditor(
                modes=["python"],
                options={
                    "mode": "python",
                    "lineNumbers": True,
                    "indentUnit": 4,
                    "tabSize": 4,
                    "indentWithTabs": False,
                    "matchBrackets": True,
                    "lineWrapping": True,
                },
                attrs={
                    "style": "min-height: 400px; width: 100%;",
                },
            ),
        }

    def clean_python_render_code(self):
        """Validate the python render code before saving."""
        render_code = self.cleaned_data.get("python_render_code", "")

        # Code is required for RenderTemplate
        if not render_code.strip():
            raise ValidationError("Render code is required")

        # Validate the render code
        try:
            validate_render_code(render_code)
        except RenderValidationError as e:
            raise ValidationError(f"Invalid render code: {e}") from e

        return render_code


@admin.register(RenderTemplate)
class RenderTemplateAdmin(admin.ModelAdmin):
    form = RenderTemplateAdminForm
    list_display = ["name", "description", "created_at", "updated_at"]
    search_fields = ["name", "description"]
    list_per_page = 25
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["name"]

    fieldsets = (
        (None, {"fields": ("name", "description")}),
        (
            "Python Render Code",
            {
                "fields": ("python_render_code",),
                "classes": ("wide",),
                "description": (
                    "Python code defining a render(card_template, qso) function that returns a PIL Image. "
                    "Code is executed in a sandboxed environment with 10-second timeout and 200MB memory limit."
                ),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(CardTemplate)
class CardTemplateAdmin(admin.ModelAdmin):
    form = CardTemplateAdminForm
    list_display = [
        "name",
        "language",
        "is_active",
        "render_template",
        "example_preview_thumbnail",
        "created_at",
        "updated_at",
    ]
    list_filter = ["is_active", "language", "render_template", "created_at"]
    search_fields = ["name", "description"]
    list_per_page = 25
    readonly_fields = ["created_at", "updated_at", "image_preview", "example_render_preview"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("name", "description", "language", "is_active")}),
        ("Card Design", {"fields": ("image", "image_preview")}),
        ("Rendering", {"fields": ("render_template",)}),
        (
            "Example Preview",
            {"fields": ("example_render_preview",), "description": "Preview of rendered card with example QSO data"},
        ),
        ("Email Template", {"fields": ("html_template",), "classes": ("wide",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Card Image")
    def image_preview(self, obj):
        """Display a preview of the card template image."""
        if obj.image:
            from django.utils.html import format_html

            return format_html('<img src="{}" style="max-height: 100px; max-width: 200px;" />', obj.image.url)
        return "No image"

    @admin.display(description="Example Preview")
    def example_preview_thumbnail(self, obj):
        """Display a small thumbnail of the rendered example in list view with hover zoom."""
        if not obj.pk or not obj.render_template:
            return "—"

        from django.utils.html import format_html

        try:
            thumbnail_url = obj.get_example_preview_data_url(max_width=200)
            fullsize_url = obj.get_example_preview_data_url(max_width=400)

            if thumbnail_url and fullsize_url:
                # Use a unique ID for this preview
                preview_id = f"preview_{obj.pk}"
                return format_html(
                    '<div class="preview-hover-container">'
                    '<img id="{}" src="{}" style="max-height: 80px; max-width: 200px; border: 1px solid #ccc; cursor: pointer;" title="Hover to see full size" />'
                    "</div>"
                    '<div id="{}_fullsize" class="preview-hover-fullsize" style="'
                    "display: none; position: fixed; z-index: 99999; "
                    "border: 3px solid #417690; box-shadow: 0 4px 12px rgba(0,0,0,0.3); "
                    'background: white; padding: 5px; border-radius: 4px; pointer-events: none;">'
                    '<img src="{}" style="max-width: 400px; max-height: 300px; display: block;" />'
                    "</div>"
                    "<script>"
                    "(function() {{"
                    '  var thumb = document.getElementById("{}");'
                    '  var fullsize = document.getElementById("{}_fullsize");'
                    "  if (thumb && fullsize) {{"
                    '    thumb.addEventListener("mouseenter", function(e) {{'
                    "      var rect = thumb.getBoundingClientRect();"
                    "      var left = rect.right + 10;"
                    "      var top = rect.top;"
                    "      if (left + 420 > window.innerWidth) {{"
                    "        left = rect.left - 420;"
                    "      }}"
                    '      fullsize.style.left = left + "px";'
                    '      fullsize.style.top = top + "px";'
                    '      fullsize.style.display = "block";'
                    "    }});"
                    '    thumb.addEventListener("mouseleave", function(e) {{'
                    '      fullsize.style.display = "none";'
                    "    }});"
                    "  }}"
                    "}})();"
                    "</script>",
                    preview_id,
                    thumbnail_url,
                    preview_id,
                    fullsize_url,
                    preview_id,
                    preview_id,
                )
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Failed to generate preview thumbnail: {e}")

        return "Error"

    @admin.display(description="Rendered Example")
    def example_render_preview(self, obj):
        """Display a larger preview of the rendered example in detail view."""
        if not obj.pk or not obj.render_template:
            return "No render template assigned"

        from django.utils.html import format_html

        try:
            data_url = obj.get_example_preview_data_url(max_width=600)
            if data_url:
                return format_html(
                    '<div style="margin: 10px 0;">'
                    '<img src="{}" style="max-width: 100%; border: 2px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />'
                    '<p style="color: #666; font-size: 12px; margin-top: 5px;">Example QSL card rendered with sample data</p>'
                    "</div>",
                    data_url,
                )
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Failed to generate preview: {e}")
            return format_html('<p style="color: red;">Error rendering preview: {}</p>', str(e))

        return "Unable to render preview"


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
