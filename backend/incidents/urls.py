from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListCreateView,
    EmergencyAlertCancelView,
    EmergencyAlertListCreateView,
    EmergencyProtocolDetailView,
    EmergencyProtocolListCreateView,
    IncidentAssignView,
    IncidentDetailView,
    IncidentEvidenceView,
    IncidentEventsView,
    IncidentListCreateView,
    IncidentStatusView,
    PushDeviceRegistrationView,
)

urlpatterns = [
    path("incidents/", IncidentListCreateView.as_view(), name="incident-list"),
    path("incidents/<int:pk>/evidence/", IncidentEvidenceView.as_view(), name="incident-evidence"),
    path("incidents/<int:pk>/", IncidentDetailView.as_view(), name="incident-detail"),
    path("incidents/<int:pk>/assign/", IncidentAssignView.as_view(), name="incident-assign"),
    path("incidents/<int:pk>/status/", IncidentStatusView.as_view(), name="incident-status"),
    path("incidents/<int:pk>/events/", IncidentEventsView.as_view(), name="incident-events"),
    path("categories/", CategoryListCreateView.as_view(), name="category-list"),
    path("categories/<int:pk>/", CategoryDetailView.as_view(), name="category-detail"),
    path("emergencies/", EmergencyProtocolListCreateView.as_view(), name="emergency-list"),
    path("emergencies/<int:pk>/", EmergencyProtocolDetailView.as_view(), name="emergency-detail"),
    path("emergency-alerts/", EmergencyAlertListCreateView.as_view(), name="emergency-alert-list"),
    path(
        "emergency-alerts/<int:pk>/cancel/",
        EmergencyAlertCancelView.as_view(),
        name="emergency-alert-cancel",
    ),
    path("push-devices/", PushDeviceRegistrationView.as_view(), name="push-device-register"),
    path(
        "push-devices/<int:pk>/",
        PushDeviceRegistrationView.as_view(),
        name="push-device-detail",
    ),
]
