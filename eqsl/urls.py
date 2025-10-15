"""
URL configuration for eqsl app.
"""

from django.urls import path

from .views import QSODetailView, QSOListView

app_name = "eqsl"

urlpatterns = [
    path("qsos/", QSOListView.as_view(), name="qso_list"),
    path("qsos/<int:pk>/", QSODetailView.as_view(), name="qso_detail"),
]
