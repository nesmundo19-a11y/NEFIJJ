from django.conf import settings
from django.db import models


class Category(models.Model):
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.PROTECT,
        related_name="categories",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "incidents_category"
        ordering = ["name"]
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_category_name_per_organization",
            ),
        ]

    def __str__(self):
        return self.name


class Incident(models.Model):
    class Status(models.TextChoices):
        PENDING = "pendiente", "Pendiente"
        IN_PROGRESS = "en_proceso", "En proceso"
        RESOLVED = "resuelta", "Resuelta"
        CLOSED = "cerrada", "Cerrada"

    class Priority(models.TextChoices):
        LOW = "baja", "Baja"
        MEDIUM = "media", "Media"
        HIGH = "alta", "Alta"
        CRITICAL = "critica", "Crítica"

    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    priority = models.CharField(max_length=50, choices=Priority.choices, default=Priority.MEDIUM)
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.PROTECT,
        related_name="incidents",
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="incidents")
    location = models.ForeignKey("accounts.Location", on_delete=models.PROTECT, related_name="incidents")
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reported_incidents",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_incidents",
    )
    evidence_image = models.ImageField(
        upload_to="evidences/%Y/%m/",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "incidents_incident"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["location", "status"]),
            models.Index(fields=["reported_by", "created_at"]),
            models.Index(fields=["assigned_to", "status"]),
        ]

    def __str__(self):
        return f"#{self.pk} {self.title}"


class IncidentEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "created", "Creada"
        ASSIGNED = "assigned", "Asignada"
        STATUS_CHANGED = "status_changed", "Cambio de estado"

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="incident_events",
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "incidents_incidentevent"
        ordering = ["created_at", "id"]


class EmergencyProtocol(models.Model):
    location = models.ForeignKey(
        "accounts.Location",
        on_delete=models.PROTECT,
        related_name="emergency_protocols",
    )
    title = models.CharField(max_length=150)
    content = models.TextField()
    contact_phone = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "incidents_emergencyprotocol"
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.location.code})"
