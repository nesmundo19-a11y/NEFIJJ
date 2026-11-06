from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models


class Organization(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activa"
        SUSPENDED = "suspended", "Suspendida"

    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "organization_admin", "Administrador de organización"
        TECHNICIAN = "technician", "Técnico"
        USER = "user", "Usuario"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    location = models.ForeignKey(
        "accounts.Location",
        on_delete=models.PROTECT,
        related_name="organization_memberships",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    role = models.CharField(max_length=30, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["organization__name", "user__username"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_user_organization_membership",
            ),
            models.CheckConstraint(
                condition=models.Q(role="organization_admin")
                | models.Q(location__isnull=False),
                name="organization_member_requires_location",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["organization", "role", "is_active"]),
        ]

    def clean(self):
        if self.role != self.Role.ADMIN and self.location_id is None:
            raise ValidationError({"location": "Los miembros deben tener una sede asignada."})
        if (
            self.location_id is not None
            and self.organization_id is not None
            and self.location.organization_id != self.organization_id
        ):
            raise ValidationError({"location": "La sede debe pertenecer a la organización."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.organization} ({self.role})"


class OrganizationInvitation(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="invitations",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="created_organization_invitations",
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="used_organization_invitations",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "expires_at"]),
        ]

    def __str__(self):
        return f"Invitación de {self.organization} ({self.created_at:%Y-%m-%d})"


class Location(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="locations",
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class NEFIJJUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.SUPERADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = "superadmin", "Superadministrador de plataforma"
        ADMIN = "admin", "Administrador"
        TECHNICIAN = "technician", "Técnico"
        STUDENT = "student", "Usuario/estudiante"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=["admin", "superadmin"])
                | models.Q(location__isnull=False),
                name="user_non_admin_requires_location",
            ),
        ]

    objects = NEFIJJUserManager()

    def clean(self):
        super().clean()
        if self.role not in {self.Role.ADMIN, self.Role.SUPERADMIN} and self.location_id is None:
            raise ValidationError({"location": "Técnicos y estudiantes deben pertenecer a una sede."})

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.SUPERADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
