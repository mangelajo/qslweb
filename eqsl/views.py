from django.db.models import Q
from django.views.generic import DetailView, ListView

from .models import QSO


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

        return queryset

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

        return context


class QSODetailView(DetailView):
    """Detail view for a single QSO record."""

    model = QSO
    template_name = "eqsl/qso_detail.html"
    context_object_name = "qso"
