import hashlib
import secrets

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import get_md5_hash_password
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

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
    ChangePasswordSerializer,
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
            "location_id": self.user.location_id,
            "organizations": OrganizationMembershipSerializer(
                memberships,
                many=True,
            ).data,
        }
        return data


class NEFIJJTokenObtainPairView(TokenObtainPairView):
    serializer_class = NEFIJJTokenObtainPairSerializer
    throttle_scope = "auth"


class NEFIJJTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])
        user_id = refresh.get(api_settings.USER_ID_CLAIM)
        user = User.objects.filter(
            **{api_settings.USER_ID_FIELD: user_id},
        ).first()
        if user is None or not user.is_active:
            raise InvalidToken("El token no es válido.")
        if refresh.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(
            user.password
        ):
            raise InvalidToken("La contraseña cambió; inicia sesión nuevamente.")
        return super().validate(attrs)


class NEFIJJTokenRefreshView(TokenRefreshView):
    serializer_class = NEFIJJTokenRefreshSerializer


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "auth"

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            user.set_password(serializer.validated_data["new_password"])
            user.save(update_fields=["password"])

        return Response(status=204)


class AdminOnlyMixin:
    permission_classes = [IsAuthenticated, IsNEFIJJAdmin]


class OrganizationPagination(PageNumberPagination):
    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data["summary"] = Organization.objects.aggregate(
            total=Count("pk"),
            active=Count("pk", filter=Q(status=Organization.Status.ACTIVE)),
            suspended=Count("pk", filter=Q(status=Organization.Status.SUSPENDED)),
        )
        return response


class OrganizationListCreateView(generics.ListCreateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    pagination_class = OrganizationPagination
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
            organization_memberships__is_active=True,
        ).distinct()

    def perform_create(self, serializer):
        organization = require_active_organization(self.request)
        role = serializer.validated_data["role"]
        if role == OrganizationMembership.Role.ADMIN and not self.request.user.is_superuser:
            raise PermissionDenied(
                "Solo el superadministrador puede asignar administradores organizacionales."
            )
        location = serializer.validated_data.get("location")
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
                is_active=user.is_active,
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
            organization_memberships__is_active=True,
        ).distinct()

    def perform_update(self, serializer):
        organization = require_active_organization(self.request)
        membership = get_object_or_404(
            OrganizationMembership,
            organization=organization,
            user=serializer.instance,
            is_active=True,
        )
        role = serializer.validated_data.get("role", membership.role)
        if role == OrganizationMembership.Role.ADMIN and not self.request.user.is_superuser:
            raise PermissionDenied(
                "Solo el superadministrador puede asignar administradores organizacionales."
            )
        location = serializer.validated_data.get("location", serializer.instance.location)
        if location is not None and location.organization_id != organization.pk:
            raise ValidationError({"location_id": "La sede debe pertenecer a la organización activa."})
        with transaction.atomic():
            user = serializer.save()
            OrganizationMembership.objects.filter(
                organization=organization,
                user=user,
            ).update(
                role=role,
                location=location,
                is_active=user.is_active,
            )


class CreateInvitationView(APIView):
    permission_classes = [IsAuthenticated, IsNEFIJJAdmin]

    def get(self, request, pk):
        organization = get_object_or_404(Organization, pk=pk)
        current_organization = get_selected_organization(request)
        if current_organization is None or current_organization.pk != organization.pk:
            raise PermissionDenied("No tienes permiso para consultar invitaciones de esa organización.")
        invitations = OrganizationInvitation.objects.filter(
            organization=organization,
            used_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).values("id", "created_at", "expires_at")
        return Response(list(invitations))

    def post(self, request, pk):
        organization = get_object_or_404(Organization, pk=pk)
        current_organization = get_selected_organization(request)
        if current_organization is None or current_organization.pk != organization.pk:
            raise PermissionDenied("No tienes permiso para invitar usuarios a esa organización.")
        if not organization.is_active:
            raise PermissionDenied("No se pueden emitir invitaciones para una organización suspendida.")
        if not Location.objects.filter(
            organization=organization,
            is_active=True,
        ).exists():
            raise ValidationError(
                {"invitation": "La organización debe tener al menos una sede activa para invitar usuarios."}
            )

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


class PreviewInvitationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code")
        if not isinstance(code, str) or not code:
            raise ValidationError({"code": "El código de invitación es obligatorio."})

        token_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
        invitation = OrganizationInvitation.objects.select_related("organization").filter(
            token_hash=token_hash,
        ).first()
        now = timezone.now()
        if (
            invitation is None
            or invitation.revoked_at is not None
            or invitation.used_at is not None
            or invitation.expires_at <= now
            or not invitation.organization.is_active
        ):
            raise ValidationError({"code": "La invitación no es válida o ya expiró."})

        locations = Location.objects.filter(
            organization=invitation.organization,
            is_active=True,
        ).values("id", "name")
        return Response(
            {
                "organization_id": invitation.organization_id,
                "organization_name": invitation.organization.name,
                "locations": list(locations),
            }
        )


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
