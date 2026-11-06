from rest_framework import serializers

from accounts.models import Location

from .models import Category, EmergencyProtocol, Incident, IncidentEvent


class CategorySerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "organization_id", "name", "description", "is_active")
        read_only_fields = ("id",)


class IncidentSerializer(serializers.ModelSerializer):
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
