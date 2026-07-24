"""
URL configuration for eqsl app.
"""

from django.urls import path

from .views import (
    ADIFImportView,
    BatchSendView,
    DashboardView,
    EnrichMissingView,
    EnrichQSOView,
    EQSLListView,
    LOTWSyncView,
    QSOCardPreviewView,
    QSODetailView,
    QSOListView,
    SendEQSLView,
    SettingsView,
    TestEmailView,
    TestQRZView,
)

app_name = "eqsl"

urlpatterns = [
    path("", DashboardView.as_view(), name="home"),
    path("qsos/", QSOListView.as_view(), name="qso_list"),
    path("qsos/<int:pk>/", QSODetailView.as_view(), name="qso_detail"),
    path("qsos/<int:pk>/send/", SendEQSLView.as_view(), name="qso_send"),
    path("qsos/<int:pk>/enrich/", EnrichQSOView.as_view(), name="qso_enrich"),
    path("qsos/enrich-missing/", EnrichMissingView.as_view(), name="enrich_missing"),
    path("qsos/<int:pk>/card.png", QSOCardPreviewView.as_view(), name="qso_card_preview"),
    path("eqsls/", EQSLListView.as_view(), name="eqsl_list"),
    path("eqsls/send-batch/", BatchSendView.as_view(), name="batch_send"),
    path("import/", ADIFImportView.as_view(), name="adif_import"),
    path("import/lotw/", LOTWSyncView.as_view(), name="lotw_sync"),
    path("settings/", SettingsView.as_view(), name="settings"),
    path("settings/test-email/", TestEmailView.as_view(), name="test_email"),
    path("settings/test-qrz/", TestQRZView.as_view(), name="test_qrz"),
]
