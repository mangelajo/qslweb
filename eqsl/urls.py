"""
URL configuration for eqsl app.
"""

from django.urls import path

from .views import DashboardView, EQSLListView, QSOCardPreviewView, QSODetailView, QSOListView, SendEQSLView

app_name = "eqsl"

urlpatterns = [
    path("", DashboardView.as_view(), name="home"),
    path("qsos/", QSOListView.as_view(), name="qso_list"),
    path("qsos/<int:pk>/", QSODetailView.as_view(), name="qso_detail"),
    path("qsos/<int:pk>/send/", SendEQSLView.as_view(), name="qso_send"),
    path("qsos/<int:pk>/card.png", QSOCardPreviewView.as_view(), name="qso_card_preview"),
    path("eqsls/", EQSLListView.as_view(), name="eqsl_list"),
]
