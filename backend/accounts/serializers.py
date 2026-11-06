from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Location, Organization, OrganizationMembership

User = get_user_model()


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ("id", "name", "code", "is_active", "created_at")
        read_only_fields = ("id", "created_at")


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name", "slug", "status", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_status = serializers.CharField(source="organization.status", read_only=True)
    location_id = serializers.IntegerField(read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True, allow_null=True)

    class Meta:
        model = OrganizationMembership
        fields = (
            "organization_id",
            "organization_name",
            "organization_status",
            "role",
            "location_id",
            "location_name",
        )


class UserManagementSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(
        choices=OrganizationMembership.Role.choices,
        required=False,
    )
    is_active = serializers.BooleanField(required=False)
    password = serializers.CharField(
        write_only=True,
        required=False,
        min_length=12,
        style={"input_type": "password"},
    )
    location_id = serializers.PrimaryKeyRelatedField(
        source="location",
        queryset=Location.objects.filter(is_active=True),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "role", "location_id", "is_active")
        read_only_fields = ("id",)
        extra_kwargs = {
            "username": {"required": True},
            "email": {"required": True},
        }

    def validate(self, attrs):
        role = attrs.get("role")
        location = attrs.get("location", getattr(self.instance, "location", None))
        if role is None and self.instance is not None:
            role = {
                User.Role.ADMIN: OrganizationMembership.Role.ADMIN,
                User.Role.TECHNICIAN: OrganizationMembership.Role.TECHNICIAN,
                User.Role.STUDENT: OrganizationMembership.Role.USER,
            }.get(self.instance.role)

        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "La contraseña es obligatoria."})
        if self.instance is None and role is None:
            raise serializers.ValidationError({"role": "El rol es obligatorio."})
        if role != OrganizationMembership.Role.ADMIN and (
            location is None or not location.is_active
        ):
            raise serializers.ValidationError(
                {"location_id": "Técnicos y estudiantes deben pertenecer a una sede activa."}
            )
        if self.instance and self.instance.is_superuser:
            raise serializers.ValidationError(
                "Las cuentas superusuario se gestionan fuera de esta API."
            )
        if "password" in attrs:
            user = self.instance or User(**attrs)
            try:
                validate_password(attrs["password"], user)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        membership_role = validated_data.pop("role")
        validated_data["role"] = self._user_role_for_membership(membership_role)
        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        membership_role = validated_data.pop("role", None)
        if membership_role is not None:
            validated_data["role"] = self._user_role_for_membership(membership_role)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

    @staticmethod
    def _user_role_for_membership(membership_role):
        return {
            OrganizationMembership.Role.ADMIN: User.Role.ADMIN,
            OrganizationMembership.Role.TECHNICIAN: User.Role.TECHNICIAN,
            OrganizationMembership.Role.USER: User.Role.STUDENT,
        }[membership_role]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is not None and instance.is_superuser:
            data["role"] = "superadmin"
        elif request is not None:
            organization = getattr(request, "_selected_organization", None)
            if organization is not None:
                membership = OrganizationMembership.objects.filter(
                    organization=organization,
                    user=instance,
                    is_active=True,
                ).first()
                if membership is not None:
                    data["role"] = membership.role
                    data["location_id"] = membership.location_id
        return data
