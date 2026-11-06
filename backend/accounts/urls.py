from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CreateInvitationView,
    JoinOrganizationView,
    LocationDetailView,
    LocationListCreateView,
    NEFIJJTokenObtainPairView,
    MyOrganizationsView,
    OrganizationListCreateView,
    OrganizationStatusView,
    RevokeInvitationView,
    UserDetailView,
    UserListCreateView,
)

urlpatterns = [
    path("auth/token/", NEFIJJTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("organizations/", OrganizationListCreateView.as_view(), name="organization-list"),
    path(
        "organizations/<int:pk>/status/",
        OrganizationStatusView.as_view(),
        name="organization-status",
    ),
    path("organizations/mine/", MyOrganizationsView.as_view(), name="my-organizations"),
    path(
        "organizations/<int:pk>/invitations/",
        CreateInvitationView.as_view(),
        name="organization-invitations",
    ),
    path(
        "organizations/<int:pk>/invitations/<int:invitation_pk>/revoke/",
        RevokeInvitationView.as_view(),
        name="organization-invitation-revoke",
    ),
    path("memberships/join/", JoinOrganizationView.as_view(), name="membership-join"),
    path("locations/", LocationListCreateView.as_view(), name="location-list"),
    path("locations/<int:pk>/", LocationDetailView.as_view(), name="location-detail"),
    path("users/", UserListCreateView.as_view(), name="user-list"),
    path("users/<int:pk>/", UserDetailView.as_view(), name="user-detail"),
]
