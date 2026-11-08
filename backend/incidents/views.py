import mimetypes

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Location, OrganizationMembership, User
from accounts.permissions import IsNEFIJJAdmin
from accounts.tenancy import (
    get_active_membership,
    get_selected_organization,
    is_organization_admin,
    require_active_organization,
    scope_to_organization,
)

from .models import (
    Category,
    EmergencyAlert,
    EmergencyAlertDelivery,
    EmergencyProtocol,
    Incident,
    IncidentEvent,
    PushDevice,
)
from .serializers import (
    CategorySerializer,
    EmergencyAlertCreateSerializer,
    EmergencyAlertSerializer,
    EmergencyProtocolSerializer,
    IncidentEventSerializer,
    IncidentSerializer,
    PushDeviceSerializer,
)


def visible_incidents(request):
    user = request.user
    queryset = Incident.objects.select_related(
        "category",
        "location",
        "reported_by",
        "assigned_to",
        "organization",
    )
    if user.is_superuser:
        return scope_to_organization(queryset, request)

    membership = get_active_membership(request)
    queryset = queryset.filter(organization_id=membership.organization_id)
    if membership.role == OrganizationMembership.Role.ADMIN:
        return queryset
    if membership.role == OrganizationMembership.Role.TECHNICIAN:
        return queryset.filter(location_id=membership.location_id)
    return queryset.filter(reported_by=user)


def apply_incident_filters(request, queryset):
    status_value = request.query_params.get("status")
    if status_value:
        if status_value not in Incident.Status.values:
            raise ValidationError({"status": "Estado no válido."})
        queryset = queryset.filter(status=status_value)

    priority_value = request.query_params.get("priority")
    if priority_value:
        if priority_value not in Incident.Priority.values:
            raise ValidationError({"priority": "Prioridad no válida."})
        queryset = queryset.filter(priority=priority_value)

    category_value = request.query_params.get("category")
    if category_value:
        try:
            category_id = int(category_value)
        except ValueError as exc:
            raise ValidationError({"category": "Debe ser un identificador numérico."}) from exc
        queryset = queryset.filter(category_id=category_id)

    location_value = request.query_params.get("location")
    if location_value:
        if not is_organization_admin(request):
            raise PermissionDenied("Solo un administrador puede filtrar por sede.")
        try:
            location_id = int(location_value)
        except ValueError as exc:
            raise ValidationError({"location": "Debe ser un identificador numérico."}) from exc
        location = get_object_or_404(
            scope_to_organization(Location.objects.all(), request),
            pk=location_id,
        )
        queryset = queryset.filter(location=location)

    return queryset


class IncidentListCreateView(generics.ListCreateAPIView):
    serializer_class = IncidentSerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        return apply_incident_filters(self.request, visible_incidents(self.request))

    def perform_create(self, serializer):
        membership = get_active_membership(self.request)
        if membership.role != OrganizationMembership.Role.USER:
            raise PermissionDenied("Solo un usuario final puede reportar incidencias.")
        organization = require_active_organization(self.request)
        user = self.request.user
        location = membership.location
        if location is None or location.organization_id != organization.pk or not location.is_active:
            raise PermissionDenied("La cuenta no tiene una sede activa asignada.")
        category = serializer.validated_data["category"]
        if category.organization_id != organization.pk:
            raise ValidationError({"category_id": "La categoría no pertenece a la organización activa."})
        with transaction.atomic():
            incident = serializer.save(
                reported_by=user,
                location=location,
                organization=organization,
                status=Incident.Status.PENDING,
            )
            IncidentEvent.objects.create(
                incident=incident,
                actor=user,
                event_type=IncidentEvent.EventType.CREATED,
                new_value={"status": incident.status},
            )


class IncidentDetailView(generics.RetrieveAPIView):
    serializer_class = IncidentSerializer

    def get_queryset(self):
        return visible_incidents(self.request)


class IncidentEvidenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        incident = get_object_or_404(visible_incidents(request), pk=pk)
        if not incident.evidence_image:
            raise Http404
        if not default_storage.exists(incident.evidence_image.name):
            raise Http404

        content_type, _ = mimetypes.guess_type(incident.evidence_image.name)
        response = FileResponse(
            default_storage.open(incident.evidence_image.name, "rb"),
            content_type=content_type or "application/octet-stream",
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response


class IncidentAssignmentSerializer(serializers.Serializer):
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.filter(
            role=User.Role.TECHNICIAN,
            is_active=True,
        ),
        allow_null=True,
    )


class IncidentAssignView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not is_organization_admin(request):
            raise PermissionDenied("Solo un administrador puede asignar incidencias.")

        with transaction.atomic():
            incident = get_object_or_404(
                scope_to_organization(
                    Incident.objects.select_related("organization").select_for_update(),
                    request,
                ),
                pk=pk,
            )
            if not incident.organization.is_active:
                raise PermissionDenied("La organización de la incidencia está suspendida.")
            serializer = IncidentAssignmentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            technician = serializer.validated_data["assigned_to"]
            if technician is not None:
                membership = OrganizationMembership.objects.filter(
                    organization=incident.organization,
                    user=technician,
                    role=OrganizationMembership.Role.TECHNICIAN,
                    is_active=True,
                    location=incident.location,
                ).first()
                if membership is None or not technician.is_active:
                    raise ValidationError(
                        {"assigned_to": "El técnico debe estar activo y pertenecer a la sede y organización."}
                    )
            previous_assignee = incident.assigned_to_id
            incident.assigned_to = technician
            incident.save(update_fields=["assigned_to", "updated_at"])
            IncidentEvent.objects.create(
                incident=incident,
                actor=request.user,
                event_type=IncidentEvent.EventType.ASSIGNED,
                old_value={"assigned_to": previous_assignee},
                new_value={"assigned_to": technician.pk if technician else None},
            )

        return Response(IncidentSerializer(incident, context={"request": request}).data)


class IncidentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Incident.Status.choices)


class IncidentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        serializer = IncidentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]

        with transaction.atomic():
            queryset = scope_to_organization(
                Incident.objects.select_related("organization").select_for_update(),
                request,
            )
            if request.user.is_superuser:
                membership_role = "superadmin"
            else:
                membership = get_active_membership(request)
                membership_role = membership.role
                if membership_role == OrganizationMembership.Role.TECHNICIAN:
                    queryset = queryset.filter(location_id=membership.location_id)
                elif membership_role != OrganizationMembership.Role.ADMIN:
                    raise PermissionDenied("No tiene permiso para cambiar el estado.")
            incident = get_object_or_404(queryset, pk=pk)
            if not incident.organization.is_active:
                raise PermissionDenied("La organización de la incidencia está suspendida.")
            if membership_role in {
                "superadmin",
                OrganizationMembership.Role.ADMIN,
            }:
                allowed_transitions = {
                    Incident.Status.RESOLVED: {Incident.Status.CLOSED},
                    Incident.Status.CLOSED: {Incident.Status.IN_PROGRESS},
                }
            elif membership_role == OrganizationMembership.Role.TECHNICIAN:
                if incident.assigned_to_id != request.user.pk:
                    raise PermissionDenied("Solo el técnico asignado puede actualizar el estado.")
                allowed_transitions = {
                    Incident.Status.PENDING: {Incident.Status.IN_PROGRESS},
                    Incident.Status.IN_PROGRESS: {Incident.Status.RESOLVED},
                }

            if new_status not in allowed_transitions.get(incident.status, set()):
                raise ValidationError({"status": "La transición de estado no está permitida."})

            previous_status = incident.status
            incident.status = new_status
            incident.save(update_fields=["status", "updated_at"])
            IncidentEvent.objects.create(
                incident=incident,
                actor=request.user,
                event_type=IncidentEvent.EventType.STATUS_CHANGED,
                old_value={"status": previous_status},
                new_value={"status": new_status},
            )

        return Response(IncidentSerializer(incident, context={"request": request}).data)


class IncidentEventsView(generics.ListAPIView):
    serializer_class = IncidentEventSerializer

    def get_queryset(self):
        incident = get_object_or_404(visible_incidents(self.request), pk=self.kwargs["pk"])
        return incident.events.select_related("actor")


class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        if self.request.method == "POST":
            permissions.append(IsNEFIJJAdmin())
        return permissions

    def get_queryset(self):
        queryset = scope_to_organization(Category.objects.all(), self.request)
        if not is_organization_admin(self.request):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        if not is_organization_admin(self.request):
            raise PermissionDenied("Solo un administrador puede crear categorías.")
        serializer.save(organization=require_active_organization(self.request))


class CategoryDetailView(generics.RetrieveUpdateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        if self.request.method in {"PATCH", "PUT"}:
            permissions.append(IsNEFIJJAdmin())
        return permissions

    def get_queryset(self):
        return scope_to_organization(Category.objects.all(), self.request)

    def get_object(self):
        if not is_organization_admin(self.request):
            raise PermissionDenied("Solo un administrador puede consultar esta categoría.")
        return super().get_object()

    def perform_update(self, serializer):
        organization = require_active_organization(self.request)
        if serializer.instance.organization_id != organization.pk:
            raise PermissionDenied("La categoría no pertenece a la organización activa.")
        serializer.save()


class EmergencyProtocolListCreateView(generics.ListCreateAPIView):
    serializer_class = EmergencyProtocolSerializer

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        if self.request.method == "POST":
            permissions.append(IsNEFIJJAdmin())
        return permissions

    def get_queryset(self):
        queryset = EmergencyProtocol.objects.select_related("location")
        organization = get_selected_organization(self.request)
        if self.request.user.is_superuser:
            if organization is not None:
                queryset = queryset.filter(location__organization=organization)
            location_id = self.request.query_params.get("location")
            if location_id is None:
                return queryset.filter(is_active=True)
            try:
                location_id = int(location_id)
            except ValueError as exc:
                raise ValidationError({"location": "Debe ser un identificador numérico."}) from exc
            return queryset.filter(location_id=location_id, is_active=True)
        membership = get_active_membership(self.request)
        queryset = queryset.filter(location__organization=membership.organization)
        if membership.role == OrganizationMembership.Role.ADMIN:
            location_id = self.request.query_params.get("location")
            if location_id:
                queryset = queryset.filter(location_id=location_id)
            return queryset.filter(is_active=True)
        user_location = membership.location
        if user_location is None or not user_location.is_active:
            return queryset.none()
        return queryset.filter(location=user_location, is_active=True)

    def perform_create(self, serializer):
        if not is_organization_admin(self.request):
            raise PermissionDenied("Solo un administrador puede crear protocolos.")
        organization = require_active_organization(self.request)
        if serializer.validated_data["location"].organization_id != organization.pk:
            raise ValidationError({"location_id": "La sede debe pertenecer a la organización activa."})
        serializer.save()


class EmergencyProtocolDetailView(generics.RetrieveUpdateAPIView):
    queryset = EmergencyProtocol.objects.select_related("location", "location__organization")
    serializer_class = EmergencyProtocolSerializer

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        if self.request.method in {"PATCH", "PUT"}:
            permissions.append(IsNEFIJJAdmin())
        return permissions

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = get_selected_organization(self.request)
        if organization is not None:
            queryset = queryset.filter(location__organization=organization)
        return queryset

    def get_object(self):
        if not is_organization_admin(self.request):
            raise PermissionDenied("Solo un administrador puede consultar este protocolo.")
        return super().get_object()

    def perform_update(self, serializer):
        organization = require_active_organization(self.request)
        location = serializer.validated_data.get("location", serializer.instance.location)
        if location.organization_id != organization.pk:
            raise ValidationError({"location_id": "La sede debe pertenecer a la organización activa."})
        serializer.save()


class PushDeviceRegistrationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PushDeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            device, _ = PushDevice.objects.get_or_create(
                expo_push_token=serializer.validated_data["expo_push_token"],
                defaults={
                    "user": request.user,
                    "platform": serializer.validated_data["platform"],
                    "is_active": True,
                },
            )
            if device.user_id != request.user.pk:
                raise PermissionDenied(
                    "Este dispositivo está vinculado a otra cuenta. Cierra su sesión antes de registrarlo."
                )
            device.platform = serializer.validated_data["platform"]
            device.is_active = True
            device.save(update_fields=["platform", "is_active", "updated_at"])
        return Response(PushDeviceSerializer(device).data)

    def delete(self, request, pk):
        device = get_object_or_404(
            PushDevice.objects.filter(user=request.user),
            pk=pk,
        )
        device.is_active = False
        device.save(update_fields=["is_active", "updated_at"])
        return Response(status=204)


class EmergencyAlertListCreateView(generics.ListCreateAPIView):
    serializer_class = EmergencyAlertSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            raise PermissionDenied(
                "Selecciona una cuenta administradora de organización para operar alertas."
            )
        get_active_membership(self.request)
        organization = require_active_organization(self.request)
        return EmergencyAlert.objects.filter(
            organization=organization,
        ).select_related("created_by", "cancelled_by")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return EmergencyAlertCreateSerializer
        return EmergencyAlertSerializer

    def perform_create(self, serializer):
        if self.request.user.is_superuser:
            raise PermissionDenied("Solo un administrador de organización puede emitir alertas.")
        membership = get_active_membership(self.request)
        if membership.role != OrganizationMembership.Role.ADMIN:
            raise PermissionDenied("Solo un administrador de organización puede emitir alertas.")
        organization = require_active_organization(self.request)

        with transaction.atomic():
            alert = serializer.save(
                organization=organization,
                created_by=self.request.user,
            )
            self.created_alert = alert
            member_user_ids = OrganizationMembership.objects.filter(
                organization=organization,
                is_active=True,
                user__is_active=True,
            ).values("user_id")
            devices = PushDevice.objects.filter(
                user_id__in=member_user_ids,
                is_active=True,
            )
            EmergencyAlertDelivery.objects.bulk_create(
                [
                    EmergencyAlertDelivery(
                        alert=alert,
                        device=device,
                        kind=EmergencyAlertDelivery.Kind.ALERT,
                    )
                    for device in devices
                ]
            )

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        alert = self.get_queryset().get(pk=self.created_alert.pk)
        return Response(
            EmergencyAlertSerializer(
                alert,
                context={"request": request},
            ).data,
            status=response.status_code,
        )


class EmergencyAlertCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.is_superuser:
            raise PermissionDenied("Solo un administrador de organización puede cancelar alertas.")
        membership = get_active_membership(request)
        if membership.role != OrganizationMembership.Role.ADMIN:
            raise PermissionDenied("Solo un administrador de organización puede cancelar alertas.")
        organization = require_active_organization(request)

        with transaction.atomic():
            alert = get_object_or_404(
                EmergencyAlert.objects.select_for_update().filter(
                    organization=organization,
                ),
                pk=pk,
            )
            if alert.status == EmergencyAlert.Status.ACTIVE:
                alert.status = EmergencyAlert.Status.CANCELLED
                alert.cancelled_by = request.user
                alert.cancelled_at = timezone.now()
                alert.save(update_fields=["status", "cancelled_by", "cancelled_at"])
                alert.deliveries.filter(
                    kind=EmergencyAlertDelivery.Kind.ALERT,
                    status=EmergencyAlertDelivery.Status.PENDING,
                ).update(
                    status=EmergencyAlertDelivery.Status.CANCELLED,
                    completed_at=timezone.now(),
                    last_error="La alerta se canceló antes del envío.",
                )
                member_user_ids = OrganizationMembership.objects.filter(
                    organization=organization,
                    is_active=True,
                    user__is_active=True,
                ).values("user_id")
                devices = PushDevice.objects.filter(
                    user_id__in=member_user_ids,
                    is_active=True,
                )
                EmergencyAlertDelivery.objects.bulk_create(
                    [
                        EmergencyAlertDelivery(
                            alert=alert,
                            device=device,
                            kind=EmergencyAlertDelivery.Kind.CANCELLATION,
                        )
                        for device in devices
                    ]
                )

        return Response(
            EmergencyAlertSerializer(alert, context={"request": request}).data
        )
