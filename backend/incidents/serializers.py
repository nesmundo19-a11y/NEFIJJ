from django.urls import reverse
from rest_framework import serializers

from accounts.models import Location
from accounts.tenancy import get_selected_organization

from .models import Category, EmergencyProtocol, Incident, IncidentEvent


class ProtectedEvidenceImageField(serializers.ImageField):
    def to_representation(self, value):
        if not value:
            return None

        incident = self.parent.instance
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
