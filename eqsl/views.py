import io

from django.contrib import messages
from django.db.models import Count, Exists, OuterRef, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from .models import QSO, CardTemplate, EmailQSL, EmailTemplate, QSOQuerySet, SendingSettings
from .render import RenderError, execute_render_code
from .services import EQSLSendError, QRZAPIError, language_for_qso, send_eqsl
from .tasks import enrich_missing_emails, enrich_qso


class DashboardView(TemplateView):
    """Home page with QSO/eQSL statistics and recent activity."""

    template_name = "eqsl/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sent_statuses = QSOQuerySet.SENT_STATUSES
        context["total_qsos"] = QSO.objects.count()
        context["needs_eqsl_count"] = QSO.objects.needs_eqsl().count()
        context["eqsl_sent_count"] = QSO.objects.eqsl_sent().count()
        context["no_email_count"] = QSO.objects.filter(email="").count()
        context["failed_count"] = EmailQSL.objects.exclude(delivery_status__in=sent_statuses).count()

        context["recent_qsos"] = QSO.objects.all()[:5]
        context["recent_eqsls"] = EmailQSL.objects.select_related("qso")[:5]

        context["band_stats"] = QSO.objects.values("band").annotate(count=Count("pk")).order_by("-count")[:8]
        context["mode_stats"] = QSO.objects.values("mode").annotate(count=Count("pk")).order_by("-count")[:8]

        return context


class QSOListView(ListView):
    """List view for QSO records."""

    model = QSO
    template_name = "eqsl/qso_list.html"
    context_object_name = "qsos"
    paginate_by = 25

    def get_queryset(self):
        """Get filtered and searched queryset."""
        queryset = super().get_queryset()

        # Search functionality
        search = self.request.GET.get("q")
        if search:
            queryset = queryset.filter(
                Q(call__icontains=search)
                | Q(name__icontains=search)
                | Q(country__icontains=search)
                | Q(my_call__icontains=search)
            )

        # Filter by band
        band = self.request.GET.get("band")
        if band:
            queryset = queryset.filter(band=band)

        # Filter by mode
        mode = self.request.GET.get("mode")
        if mode:
            queryset = queryset.filter(mode=mode)

        # Filter by eQSL status
        eqsl_status = self.request.GET.get("eqsl_status")
        if eqsl_status == "needs":
            queryset = queryset.needs_eqsl()
        elif eqsl_status == "sent":
            queryset = queryset.eqsl_sent()

        # Annotate sent status for the badge column
        sent_qsls = EmailQSL.objects.filter(qso=OuterRef("pk"), delivery_status__in=QSOQuerySet.SENT_STATUSES)
        return queryset.annotate(has_sent_eqsl=Exists(sent_qsls))

    def get_context_data(self, **kwargs):
        """Add extra context for filters."""
        context = super().get_context_data(**kwargs)

        # Get unique bands and modes for filters
        context["bands"] = QSO.objects.values_list("band", flat=True).distinct().order_by("band")
        context["modes"] = QSO.objects.values_list("mode", flat=True).distinct().order_by("mode")

        # Preserve current filters in context
        context["current_band"] = self.request.GET.get("band", "")
        context["current_mode"] = self.request.GET.get("mode", "")
        context["current_search"] = self.request.GET.get("q", "")
        context["current_eqsl_status"] = self.request.GET.get("eqsl_status", "")
        context["needs_eqsl_count"] = QSO.objects.needs_eqsl().count()

        return context


class QSODetailView(DetailView):
    """Detail view for a single QSO record."""

    model = QSO
    template_name = "eqsl/qso_detail.html"
    context_object_name = "qso"

    def get_context_data(self, **kwargs):
        """Add sending form choices and history."""
        context = super().get_context_data(**kwargs)
        qso = self.object
        settings = SendingSettings.get_settings()

        context["card_templates"] = CardTemplate.objects.all()
        context["email_templates"] = EmailTemplate.objects.filter(is_active=True)
        context["default_card_template"] = settings.default_card_template or CardTemplate.objects.first()
        context["default_email_template"] = EmailTemplate.default_for_language(language_for_qso(qso))
        context["email_qsls"] = qso.email_qsls.select_related("card_template", "email_template")
        return context


class SendEQSLView(View):
    """Send an eQSL email for a QSO (POST only)."""

    def post(self, request, pk):
        qso = get_object_or_404(QSO, pk=pk)

        card_template = None
        card_template_id = request.POST.get("card_template")
        if card_template_id:
            card_template = get_object_or_404(CardTemplate, pk=card_template_id)

        email_template = None
        email_template_id = request.POST.get("email_template")
        if email_template_id:
            email_template = get_object_or_404(EmailTemplate, pk=email_template_id)

        try:
            email_qsl = send_eqsl(qso, card_template=card_template, email_template=email_template)
        except EQSLSendError as e:
            messages.error(request, f"Could not send eQSL for {qso.call}: {e}")
        else:
            if email_qsl.delivery_status == "sent":
                messages.success(request, f"eQSL sent to {qso.call} ({email_qsl.recipient_email})")
            else:
                messages.error(request, f"Sending eQSL to {qso.call} failed: {email_qsl.error_message}")

        return redirect(request.POST.get("next") or "eqsl:qso_detail", pk=qso.pk)


class EnrichQSOView(View):
    """Fill blank contact fields on a QSO from QRZ.com (POST only)."""

    def post(self, request, pk):
        qso = get_object_or_404(QSO, pk=pk)

        try:
            result = enrich_qso(qso.pk)
        except QRZAPIError as e:
            messages.error(request, f"QRZ lookup failed: {e}")
        else:
            if result["error"]:
                messages.warning(request, result["error"])
            elif result["updated"]:
                messages.success(request, f"QRZ lookup for {qso.call}: found {', '.join(result['updated'])}")
            else:
                messages.info(request, f"QRZ lookup for {qso.call}: nothing new to fill in")

        return redirect(request.POST.get("next") or "eqsl:qso_detail", pk=qso.pk)


class EnrichMissingView(View):
    """Bulk-enrich all QSOs without an email address from QRZ.com (POST only)."""

    def post(self, request):
        try:
            summary = enrich_missing_emails()
        except QRZAPIError as e:
            messages.error(request, f"QRZ lookup failed: {e}")
            return redirect("eqsl:home")

        parts = [f"{summary['processed']} QSOs looked up", f"{summary['emails_found']} emails found"]
        if summary["not_found"]:
            parts.append(f"{summary['not_found']} not on QRZ")
        if summary["skipped_recent"]:
            parts.append(f"{summary['skipped_recent']} skipped (recently checked)")
        message = "QRZ enrichment: " + ", ".join(parts)

        if summary["error"]:
            messages.error(request, f"{message} — aborted: {summary['error']}")
        elif summary["emails_found"]:
            messages.success(request, message)
        else:
            messages.info(request, message)

        return redirect(request.POST.get("next") or "eqsl:home")


class QSOCardPreviewView(View):
    """Render the QSL card for a real QSO as a PNG image."""

    def get(self, request, pk):
        qso = get_object_or_404(QSO, pk=pk)

        card_template_id = request.GET.get("card_template")
        if card_template_id:
            card_template = get_object_or_404(CardTemplate, pk=card_template_id)
        else:
            settings = SendingSettings.get_settings()
            card_template = settings.default_card_template or CardTemplate.objects.first()
        if card_template is None:
            raise Http404("No card template available")

        try:
            image = execute_render_code(card_template, qso)
        except RenderError as e:
            raise Http404(f"Card rendering failed: {e}") from e

        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="PNG")
        return HttpResponse(buffer.getvalue(), content_type="image/png")


class EQSLListView(ListView):
    """List of sent eQSL records."""

    model = EmailQSL
    template_name = "eqsl/eqsl_list.html"
    context_object_name = "email_qsls"
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related("qso", "card_template", "email_template")
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(delivery_status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_status"] = self.request.GET.get("status", "")
        context["statuses"] = [choice[0] for choice in EmailQSL._meta.get_field("delivery_status").choices]
        return context
