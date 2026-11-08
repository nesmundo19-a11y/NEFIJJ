from django.urls import reverse
from rest_framework import serializers

from accounts.models import Location, OrganizationMembership
from accounts.tenancy import get_active_membership
from accounts.tenancy import get_selected_organization

from .models import (
    Category,
    EmergencyAlert,
    EmergencyAlertDelivery,
    EmergencyProtocol,
    Incident,
    IncidentEvent,
    PushDevice,
)


class ProtectedEvidenceImageField(serializers.ImageField):
    def to_representation(self, value):
        if not value:
            return None

        incident = getattr(value, "instance", None)
        if incident is None or incident.pk is None:
            return None

        url = reverse("incident-evidence", kwargs={"pk": incident.pk})
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class CategorySerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "organization_id", "name", "description", "is_active")
        read_only_fields = ("id",)

    def validate_name(self, value):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return value

        organization = (
            self.instance.organization
            if self.instance is not None
            else get_selected_organization(request)
        )
        if organization is None:
            return value

        categories = Category.objects.filter(
            organization=organization,
            name__iexact=value,
        )
        if self.instance is not None:
            categories = categories.exclude(pk=self.instance.pk)
        if categories.exists():
            raise serializers.ValidationError(
                "Ya existe una categoría con ese nombre en esta organización."
            )
        return value


class IncidentSerializer(serializers.ModelSerializer):
    MAX_EVIDENCE_BYTES = 10 * 1024 * 1024
    ALLOWED_EVIDENCE_FORMATS = {"JPEG", "PNG"}

    evidence_image = ProtectedEvidenceImageField(required=False, allow_null=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.filter(is_active=True),
    )
    location_id = serializers.IntegerField(read_only=True)
    organization_id = serializers.IntegerField(read_only=True)
    reported_by = serializers.IntegerField(source="reported_by_id", read_only=True)
    assigned_to = serializers.IntegerField(source="assigned_to_id", read_only=True)

    class Meta:
        model = Incident
        fields = (
            "id",
            "title",
            "description",
            "status",
            "priority",
            "organization_id",
            "category_id",
            "location_id",
            "reported_by",
            "assigned_to",
            "evidence_image",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "organization_id",
            "location_id",
            "reported_by",
            "assigned_to",
            "created_at",
            "updated_at",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return

        organization = get_selected_organization(request)
        if organization is not None:
            self.fields["category_id"].queryset = Category.objects.filter(
                is_active=True,
                organization=organization,
            )

    def validate_evidence_image(self, image):
        if not image:
            return image
        if image.size > self.MAX_EVIDENCE_BYTES:
            raise serializers.ValidationError(
                "La imagen no puede superar los 10 MB."
            )
        decoded_image = getattr(image, "image", None)
        if decoded_image and decoded_image.format not in self.ALLOWED_EVIDENCE_FORMATS:
            raise serializers.ValidationError("La imagen debe ser JPG o PNG.")
        if decoded_image and decoded_image.width * decoded_image.height > 40_000_000:
            raise serializers.ValidationError(
                "La resolución de la imagen supera el límite permitido."
            )
        return image


class IncidentEventSerializer(serializers.ModelSerializer):
    actor_id = serializers.IntegerField(read_only=True)
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = IncidentEvent
        fields = (
            "id",
            "event_type",
            "actor_id",
            "actor_username",
            "old_value",
            "new_value",
            "created_at",
        )


class EmergencyProtocolSerializer(serializers.ModelSerializer):
    location_id = serializers.PrimaryKeyRelatedField(
        source="location",
        queryset=Location.objects.filter(is_active=True),
    )
    location_name = serializers.CharField(source="location.name", read_only=True)

    class Meta:
        model = EmergencyProtocol
        fields = (
            "id",
            "location_id",
            "location_name",
            "title",
            "content",
            "contact_phone",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "location_name", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return

        organization = get_selected_organization(request)
        if organization is not None:
            self.fields["location_id"].queryset = Location.objects.filter(
                is_active=True,
                organization=organization,
            )


class PushDeviceSerializer(serializers.ModelSerializer):
    expo_push_token = serializers.CharField(max_length=255, validators=[])

    class Meta:
        model = PushDevice
        fields = ("id", "expo_push_token", "platform")

    def validate_expo_push_token(self, value):
        if not value.startswith("ExponentPushToken[") and not value.startswith("ExpoPushToken["):
            raise serializers.ValidationError("El token de Expo Push no tiene un formato válido.")
        return value


class EmergencyAlertCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyAlert
        fields = ("title", "message")

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("El título no puede estar vacío.")
        return value.strip()

    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError("El mensaje no puede estar vacío.")
        return value.strip()


class EmergencyAlertSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    cancelled_by_username = serializers.CharField(
        source="cancelled_by.username",
        read_only=True,
        allow_null=True,
    )
    pending_deliveries = serializers.SerializerMethodField()
    accepted_deliveries = serializers.SerializerMethodField()
    failed_deliveries = serializers.SerializerMethodField()
    delivery_errors = serializers.SerializerMethodField()

    class Meta:
        model = EmergencyAlert
        fields = (
            "id",
            "organization_id",
            "title",
            "message",
            "status",
            "created_by_username",
            "created_at",
            "cancelled_by_username",
            "cancelled_at",
            "pending_deliveries",
            "accepted_deliveries",
            "failed_deliveries",
            "delivery_errors",
        )

    def get_pending_deliveries(self, instance):
        return instance.deliveries.filter(status=EmergencyAlertDelivery.Status.PENDING).count()

    def get_accepted_deliveries(self, instance):
        return instance.deliveries.filter(status=EmergencyAlertDelivery.Status.ACCEPTED).count()

    def get_failed_deliveries(self, instance):
        return instance.deliveries.filter(status=EmergencyAlertDelivery.Status.FAILED).count()

    def get_delivery_errors(self, instance):
        request = self.context.get("request")
        if request is None or request.user.is_superuser:
            return []
        if get_active_membership(request).role != OrganizationMembership.Role.ADMIN:
            return []
        return list(
            instance.deliveries.filter(
                status=EmergencyAlertDelivery.Status.FAILED,
            )
            .exclude(last_error="")
            .order_by("-created_at")
            .values_list("last_error", flat=True)[:10]
        )
