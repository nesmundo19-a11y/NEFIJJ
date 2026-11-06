from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListCreateView,
    EmergencyProtocolDetailView,
    EmergencyProtocolListCreateView,
    IncidentAssignView,
    IncidentDetailView,
    IncidentEventsView,
    IncidentListCreateView,
    IncidentStatusView,
)

urlpatterns = [
    path("incidents/", IncidentListCreateView.as_view(), name="incident-list"),
    path("incidents/<int:pk>/", IncidentDetailView.as_view(), name="incident-detail"),
    path("incidents/<int:pk>/assign/", IncidentAssignView.as_view(), name="incident-assign"),
    path("incidents/<int:pk>/status/", IncidentStatusView.as_view(), name="incident-status"),
    path("incidents/<int:pk>/events/", IncidentEventsView.as_view(), name="incident-events"),
    path("categories/", CategoryListCreateView.as_view(), name="category-list"),
    path("categories/<int:pk>/", CategoryDetailView.as_view(), name="category-detail"),
    path("emergencies/", EmergencyProtocolListCreateView.as_view(), name="emergency-list"),
    path("emergencies/<int:pk>/", EmergencyProtocolDetailView.as_view(), name="emergency-detail"),
]
