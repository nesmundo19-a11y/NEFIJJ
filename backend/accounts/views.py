import hashlib
import secrets

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import (
    Location,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
    User,
)
from .invitations import add_colombia_business_days
from .permissions import IsNEFIJJAdmin, IsPlatformSuperAdmin
from .serializers import (
    LocationSerializer,
    OrganizationMembershipSerializer,
    OrganizationSerializer,
    UserManagementSerializer,
)
from .tenancy import (
    get_active_membership,
    get_selected_organization,
    require_active_organization,
    scope_to_organization,
)


class NEFIJJTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        memberships = list(
            OrganizationMembership.objects.filter(
                user=self.user,
                is_active=True,
                organization__status=Organization.Status.ACTIVE,
            ).select_related("organization")
        )
        if self.user.is_superuser:
            role = "superadmin"
        elif len(memberships) == 1:
            role = memberships[0].role
        else:
            role = "member"
        data["user"] = {
            "id": self.user.pk,
            "username": self.user.username,
            "role": role,
            "location_id": memberships[0].location_id if len(memberships) == 1 else None,
            "organizations": OrganizationMembershipSerializer(
                memberships,
                many=True,
            ).data,
        }
        return data


class NEFIJJTokenObtainPairView(TokenObtainPairView):
    serializer_class = NEFIJJTokenObtainPairSerializer
    throttle_scope = "auth"


class AdminOnlyMixin:
    permission_classes = [IsAuthenticated, IsNEFIJJAdmin]


class OrganizationListCreateView(generics.ListCreateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated, IsPlatformSuperAdmin]


class OrganizationStatusView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformSuperAdmin]

    def patch(self, request, pk):
        organization = get_object_or_404(Organization, pk=pk)
        serializer = OrganizationSerializer(
            organization,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MyOrganizationsView(generics.ListAPIView):
    serializer_class = OrganizationMembershipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrganizationMembership.objects.filter(
            user=self.request.user,
            is_active=True,
            organization__status=Organization.Status.ACTIVE,
        ).select_related("organization")


class LocationListCreateView(AdminOnlyMixin, generics.ListCreateAPIView):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    def get_queryset(self):
        return scope_to_organization(super().get_queryset(), self.request)

    def perform_create(self, serializer):
        serializer.save(organization=require_active_organization(self.request))


class LocationDetailView(AdminOnlyMixin, generics.RetrieveUpdateAPIView):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    def get_queryset(self):
        return scope_to_organization(super().get_queryset(), self.request)

    def perform_update(self, serializer):
        organization = require_active_organization(self.request)
        if serializer.instance.organization_id != organization.pk:
            raise PermissionDenied("La sede no pertenece a la organización activa.")
        serializer.save()


class UserListCreateView(AdminOnlyMixin, generics.ListCreateAPIView):
    serializer_class = UserManagementSerializer

    def get_queryset(self):
        queryset = User.objects.select_related("location").all()
        organization = get_selected_organization(self.request)
        if organization is None:
            return queryset
        return queryset.filter(
            organization_memberships__organization=organization,
        ).distinct()

    def perform_create(self, serializer):
        organization = require_active_organization(self.request)
        role = serializer.validated_data["role"]
        location = serializer.validated_data.get("location")
        membership_is_active = serializer.validated_data.get("is_active", True)
        if role == OrganizationMembership.Role.ADMIN and not self.request.user.is_superuser:
            raise PermissionDenied(
                "Solo el superadministrador puede asignar administradores organizacionales."
            )
        if location is not None and location.organization_id != organization.pk:
            raise ValidationError({"location_id": "La sede debe pertenecer a la organización activa."})
        if role != OrganizationMembership.Role.ADMIN and location is None:
            raise ValidationError({"location_id": "Selecciona una sede de la organización."})
        with transaction.atomic():
            user = serializer.save()
            OrganizationMembership.objects.create(
                organization=organization,
                location=location,
                user=user,
                role=role,
                is_active=membership_is_active,
            )


class UserDetailView(AdminOnlyMixin, generics.RetrieveUpdateAPIView):
    serializer_class = UserManagementSerializer

    def get_queryset(self):
        queryset = User.objects.select_related("location").all()
        organization = get_selected_organization(self.request)
        if organization is None:
            return queryset
        return queryset.filter(
            organization_memberships__organization=organization,
        ).distinct()

    def perform_update(self, serializer):
        organization = require_active_organization(self.request)
        membership = get_object_or_404(
            OrganizationMembership,
            organization=organization,
            user=serializer.instance,
        )
        role = serializer.validated_data.get("role", membership.role)
        if role == OrganizationMembership.Role.ADMIN and not self.request.user.is_superuser:
            raise PermissionDenied(
                "Solo el superadministrador puede asignar administradores organizacionales."
            )
        location = serializer.validated_data.get("location", membership.location)
        if location is not None and (
            location.organization_id != organization.pk or not location.is_active
        ):
            raise ValidationError({"location_id": "La sede debe pertenecer a la organización activa."})
        if role != OrganizationMembership.Role.ADMIN and location is None:
            raise ValidationError({"location_id": "Selecciona una sede activa para este rol."})
        membership_is_active = serializer.validated_data.get(
            "is_active",
            membership.is_active,
        )
        with transaction.atomic():
            user = serializer.save()
            membership.role = role
            membership.location = location
            membership.is_active = membership_is_active
            membership.save(update_fields=["role", "location", "is_active"])


class CreateInvitationView(APIView):
    permission_classes = [IsAuthenticated, IsNEFIJJAdmin]

    def post(self, request, pk):
        organization = get_object_or_404(Organization, pk=pk)
        current_organization = get_selected_organization(request)
        if current_organization is None or current_organization.pk != organization.pk:
            raise PermissionDenied("No tienes permiso para invitar usuarios a esa organización.")
        if not organization.is_active:
            raise PermissionDenied("No se pueden emitir invitaciones para una organización suspendida.")

        raw_token = secrets.token_urlsafe(32)
        invitation = OrganizationInvitation.objects.create(
            organization=organization,
            token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            created_by=request.user,
            expires_at=add_colombia_business_days(timezone.now(), 7),
        )
        return Response(
            {
                "id": invitation.pk,
                "organization_id": organization.pk,
                "code": raw_token,
                "expires_at": invitation.expires_at,
            },
            status=201,
        )


class RevokeInvitationView(APIView):
    permission_classes = [IsAuthenticated, IsNEFIJJAdmin]

    def post(self, request, pk, invitation_pk):
        organization = get_object_or_404(Organization, pk=pk)
        current_organization = get_selected_organization(request)
        if current_organization is None or current_organization.pk != organization.pk:
            raise PermissionDenied("No tienes permiso para modificar invitaciones de esa organización.")
        with transaction.atomic():
            invitation = get_object_or_404(
                OrganizationInvitation.objects.select_for_update(),
                pk=invitation_pk,
                organization=organization,
            )
            if invitation.used_at is not None:
                raise ValidationError({"invitation": "La invitación ya fue utilizada."})
            if invitation.revoked_at is None:
                invitation.revoked_at = timezone.now()
                invitation.save(update_fields=["revoked_at"])
        return Response(status=204)


class JoinOrganizationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code")
        if not isinstance(code, str) or not code:
            raise ValidationError({"code": "El código de invitación es obligatorio."})
        try:
            location_id = int(request.data.get("location_id"))
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                {"location_id": "Selecciona una sede válida de la organización."}
            ) from exc
        if request.user.is_superuser:
            raise PermissionDenied("El superadministrador no puede vincularse como usuario final.")

        token_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
        with transaction.atomic():
            invitation = get_object_or_404(
                OrganizationInvitation.objects.select_for_update().select_related("organization"),
                token_hash=token_hash,
            )
            now = timezone.now()
            if (
                invitation.revoked_at is not None
                or invitation.used_at is not None
                or invitation.expires_at <= now
                or not invitation.organization.is_active
            ):
                raise ValidationError({"code": "La invitación no es válida o ya expiró."})
            location = get_object_or_404(
                Location.objects.filter(
                    organization=invitation.organization,
                    is_active=True,
                ),
                pk=location_id,
            )
            membership, created = OrganizationMembership.objects.get_or_create(
                organization=invitation.organization,
                user=request.user,
                defaults={
                    "location": location,
                    "role": OrganizationMembership.Role.USER,
                    "is_active": True,
                },
            )
            if not created:
                raise ValidationError({"code": "Ya perteneces a esta organización."})
            invitation.used_at = now
            invitation.used_by = request.user
            invitation.save(update_fields=["used_at", "used_by"])
        return Response(
            OrganizationMembershipSerializer(membership).data,
            status=201,
        )
