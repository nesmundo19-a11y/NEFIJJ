from importlib import import_module
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.urls import Resolver404, resolve, reverse
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.test import APITestCase

from accounts.models import Location, Organization, OrganizationMembership
from .models import (
    Category,
    EmergencyAlert,
    EmergencyAlertDelivery,
    EmergencyProtocol,
    Incident,
    IncidentEvent,
    PushDevice,
)
from .serializers import IncidentSerializer

create_missing_legacy_tables = import_module(
    "incidents.migrations.0004_repair_missing_legacy_tables"
).create_missing_legacy_tables


class LegacyTableRepairMigrationTests(TransactionTestCase):
    def test_creates_only_missing_tables_and_is_idempotent(self):
        state = MigrationExecutor(connection).loader.project_state(
            [("incidents", "0003_backfill_organization_scope")]
        )
        apps = state.apps
        models_to_repair = [
            apps.get_model("incidents", model_name)
            for model_name in ("IncidentEvent", "EmergencyProtocol")
        ]

        with connection.schema_editor() as schema_editor:
            existing_tables = set(connection.introspection.table_names())
            for model in models_to_repair:
                if model._meta.db_table in existing_tables:
                    schema_editor.delete_model(model)

            create_missing_legacy_tables(apps, schema_editor)
            repaired_tables = set(connection.introspection.table_names())
            create_missing_legacy_tables(apps, schema_editor)

        for model in models_to_repair:
            self.assertIn(model._meta.db_table, repaired_tables)
        self.assertEqual(
            set(connection.introspection.table_names()),
            repaired_tables,
        )


class IncidentApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.organization = Organization.objects.create(
            name="Organización de prueba",
            slug="incident-test",
        )
        self.other_organization = Organization.objects.create(
            name="Otra organización",
            slug="incident-other-test",
        )
        self.location_a = Location.objects.create(
            organization=self.organization,
            name="Sede A",
            code="A",
        )
        self.location_b = Location.objects.create(
            organization=self.organization,
            name="Sede B",
            code="B",
        )
        self.foreign_location = Location.objects.create(
            organization=self.other_organization,
            name="Sede externa",
            code="EXT",
        )
        self.category = Category.objects.create(
            organization=self.organization,
            name="Redes",
        )
        self.foreign_category = Category.objects.create(
            organization=self.other_organization,
            name="Redes",
        )
        self.student_a = user_model.objects.create_user(
            username="student_a",
            email="student_a@example.test",
            password="Secure-Test-Password-123",
            role=user_model.Role.STUDENT,
            location=self.location_a,
        )
        self.student_b = user_model.objects.create_user(
            username="student_b",
            email="student_b@example.test",
            password="Secure-Test-Password-123",
            role=user_model.Role.STUDENT,
            location=self.location_b,
        )
        self.technician_a = user_model.objects.create_user(
            username="technician_a",
            email="technician_a@example.test",
            password="Secure-Test-Password-123",
            role=user_model.Role.TECHNICIAN,
            location=self.location_a,
        )
        self.technician_b = user_model.objects.create_user(
            username="technician_b",
            email="technician_b@example.test",
            password="Secure-Test-Password-123",
            role=user_model.Role.TECHNICIAN,
            location=self.location_b,
        )
        self.admin = user_model.objects.create_user(
            username="admin",
            email="admin@example.test",
            password="Secure-Test-Password-123",
            role=user_model.Role.ADMIN,
        )
        self.superadmin = user_model.objects.create_superuser(
            username="platform_admin",
            email="platform_admin@example.test",
            password="Secure-Test-Password-123",
        )
        self.foreign_student = user_model.objects.create_user(
            username="foreign_student",
            email="foreign_student@example.test",
            password="Secure-Test-Password-123",
            role=user_model.Role.STUDENT,
            location=self.foreign_location,
        )

        for user, organization, location, role in (
            (self.student_a, self.organization, self.location_a, OrganizationMembership.Role.USER),
            (self.student_b, self.organization, self.location_b, OrganizationMembership.Role.USER),
            (
                self.technician_a,
                self.organization,
                self.location_a,
                OrganizationMembership.Role.TECHNICIAN,
            ),
            (
                self.technician_b,
                self.organization,
                self.location_b,
                OrganizationMembership.Role.TECHNICIAN,
            ),
            (self.admin, self.organization, None, OrganizationMembership.Role.ADMIN),
            (
                self.foreign_student,
                self.other_organization,
                self.foreign_location,
                OrganizationMembership.Role.USER,
            ),
        ):
            OrganizationMembership.objects.create(
                organization=organization,
                location=location,
                user=user,
                role=role,
            )

    def create_incident(self, reporter=None, location=None, assigned_to=None, status=None):
        reporter = reporter or self.student_a
        location = location or reporter.location
        incident = Incident.objects.create(
            title="Falla de red",
            description="Sin conectividad",
            organization=location.organization,
            category=self.category,
            location=location,
            reported_by=reporter,
            assigned_to=assigned_to,
        )
        if status:
            incident.status = status
            incident.save(update_fields=["status"])
        return incident

    def test_student_creation_derives_tenant_and_protected_fields(self):
        self.client.force_authenticate(self.student_a)
        response = self.client.post(
            reverse("incident-list"),
            {
                "title": "Equipo sin conexión",
                "description": "El equipo no obtiene dirección IP.",
                "category_id": self.category.pk,
                "reported_by": self.student_b.pk,
                "location_id": self.location_b.pk,
                "status": Incident.Status.CLOSED,
                "assigned_to": self.technician_b.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        incident = Incident.objects.get(pk=response.data["id"])
        self.assertEqual(incident.reported_by, self.student_a)
        self.assertEqual(incident.location, self.location_a)
        self.assertEqual(incident.status, Incident.Status.PENDING)
        self.assertIsNone(incident.assigned_to)
        self.assertEqual(incident.priority, Incident.Priority.MEDIUM)
        self.assertEqual(incident.events.get().event_type, IncidentEvent.EventType.CREATED)

    def test_invalid_incident_payloads_do_not_create_records(self):
        self.client.force_authenticate(self.student_a)
        endpoint = reverse("incident-list")

        missing_fields = self.client.post(
            endpoint,
            {"category_id": self.category.pk},
            format="json",
        )
        inactive_category = Category.objects.create(
            organization=self.organization,
            name="Inactiva",
            is_active=False,
        )
        inactive_category_response = self.client.post(
            endpoint,
            {
                "title": "Categoría inactiva",
                "description": "No debe guardarse.",
                "category_id": inactive_category.pk,
            },
            format="json",
        )
        invalid_priority = self.client.post(
            endpoint,
            {
                "title": "Prioridad desconocida",
                "description": "No debe guardarse.",
                "category_id": self.category.pk,
                "priority": "urgente",
            },
            format="json",
        )

        self.assertEqual(missing_fields.status_code, 400)
        self.assertEqual(inactive_category_response.status_code, 400)
        self.assertEqual(invalid_priority.status_code, 400)
        self.assertEqual(Incident.objects.count(), 0)

    def test_student_can_create_incident_with_multipart_evidence_image(self):
        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), color="red").save(image_buffer, format="PNG")
        image = SimpleUploadedFile(
            "evidence.png",
            image_buffer.getvalue(),
            content_type="image/png",
        )
        self.client.force_authenticate(self.student_a)

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("incident-list"),
                    {
                        "title": "Daño en el laboratorio",
                        "description": "Se adjunta evidencia.",
                        "category_id": str(self.category.pk),
                        "evidence_image": image,
                    },
                    format="multipart",
                )

                self.assertEqual(response.status_code, 201, response.data)
                incident = Incident.objects.get(pk=response.data["id"])
                self.assertTrue(incident.evidence_image.name.startswith("evidences/"))
                self.assertTrue(Path(media_root, incident.evidence_image.name).is_file())
                self.assertIn("evidence_image", response.data)
                self.assertIn(
                    reverse("incident-evidence", args=[incident.pk]),
                    response.data["evidence_image"],
                )
                list_response = self.client.get(reverse("incident-list"))
                self.assertEqual(list_response.status_code, 200, list_response.data)
                self.assertEqual(list_response.data["count"], 1)
                self.assertIn(
                    reverse("incident-evidence", args=[incident.pk]),
                    list_response.data["results"][0]["evidence_image"],
                )
                self.assertEqual(
                    incident.events.get().event_type,
                    IncidentEvent.EventType.CREATED,
                )

                evidence_response = self.client.get(
                    reverse("incident-evidence", args=[incident.pk])
                )
                self.assertEqual(evidence_response.status_code, 200)
                self.assertEqual(
                    b"".join(evidence_response.streaming_content),
                    image_buffer.getvalue(),
                )
                with self.assertRaises(Resolver404):
                    resolve(f"/media/{incident.evidence_image.name}")

                self.client.force_authenticate(self.student_b)
                foreign_evidence_response = self.client.get(
                    reverse("incident-evidence", args=[incident.pk])
                )
                self.assertEqual(foreign_evidence_response.status_code, 404)
                self.client.force_authenticate(user=None)
                unauthenticated_response = self.client.get(
                    reverse("incident-evidence", args=[incident.pk])
                )
                self.assertEqual(unauthenticated_response.status_code, 401)

    def test_evidence_image_rejects_files_over_10_megabytes(self):
        image = SimpleNamespace(size=10 * 1024 * 1024 + 1)
        with self.assertRaisesMessage(
            DRFValidationError,
            "La imagen no puede superar los 10 MB.",
        ):
            IncidentSerializer().validate_evidence_image(image)

    def test_invalid_multipart_evidence_does_not_create_incident(self):
        self.client.force_authenticate(self.student_a)

        response = self.client.post(
            reverse("incident-list"),
            {
                "title": "Archivo inválido",
                "description": "El archivo no es una imagen.",
                "category_id": str(self.category.pk),
                "evidence_image": SimpleUploadedFile(
                    "evidence.png",
                    b"not an image",
                    content_type="image/png",
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Incident.objects.count(), 0)

    def test_organization_admin_can_manage_categories_within_tenant(self):
        self.client.force_authenticate(self.admin)
        create_response = self.client.post(
            reverse("category-list"),
            {"name": "Infraestructura", "description": "Edificios y mobiliario"},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201, create_response.data)
        category_id = create_response.data["id"]
        self.assertEqual(create_response.data["organization_id"], self.organization.pk)

        update_response = self.client.patch(
            reverse("category-detail", args=[category_id]),
            {"description": "Daños a edificios y mobiliario", "is_active": False},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200, update_response.data)
        self.assertFalse(update_response.data["is_active"])

        foreign_update_response = self.client.patch(
            reverse("category-detail", args=[self.foreign_category.pk]),
            {"name": "Cambio no autorizado"},
            format="json",
        )
        self.assertEqual(foreign_update_response.status_code, 404)
        self.assertEqual(self.foreign_category.name, "Redes")

    def test_category_names_are_unique_per_organization(self):
        self.client.force_authenticate(self.admin)

        duplicate_create_response = self.client.post(
            reverse("category-list"),
            {"name": "redes", "description": "Nombre duplicado"},
            format="json",
        )
        category = Category.objects.create(
            organization=self.organization,
            name="Aseo",
        )
        duplicate_update_response = self.client.patch(
            reverse("category-detail", args=[category.pk]),
            {"name": "REDES"},
            format="json",
        )

        self.assertEqual(duplicate_create_response.status_code, 400)
        self.assertIn("name", duplicate_create_response.data)
        self.assertEqual(duplicate_update_response.status_code, 400)
        category.refresh_from_db()
        self.assertEqual(category.name, "Aseo")
        self.assertTrue(
            Category.objects.filter(
                organization=self.other_organization,
                name="Redes",
            ).exists()
        )

    def test_inactive_categories_are_hidden_from_users_and_rejected_for_reports(self):
        inactive_category = Category.objects.create(
            organization=self.organization,
            name="Categoría inactiva",
            is_active=False,
        )

        self.client.force_authenticate(self.admin)
        admin_list_response = self.client.get(reverse("category-list"))
        self.assertIn(
            inactive_category.pk,
            {item["id"] for item in admin_list_response.data["results"]},
        )

        self.client.force_authenticate(self.student_a)
        user_list_response = self.client.get(reverse("category-list"))
        report_response = self.client.post(
            reverse("incident-list"),
            {
                "title": "Reporte con categoría inactiva",
                "description": "No debe aceptarse.",
                "category_id": inactive_category.pk,
            },
            format="json",
        )

        self.assertNotIn(
            inactive_category.pk,
            {item["id"] for item in user_list_response.data["results"]},
        )
        self.assertEqual(report_response.status_code, 400)
        self.assertEqual(Incident.objects.count(), 0)

    def test_non_admin_cannot_manage_categories(self):
        self.client.force_authenticate(self.student_a)
        response = self.client.post(
            reverse("category-list"),
            {"name": "No autorizada", "description": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Category.objects.filter(
                organization=self.organization,
                name="No autorizada",
            ).exists()
        )

    def test_incident_serializer_rejects_category_from_another_organization(self):
        self.client.force_authenticate(self.student_a)

        response = self.client.post(
            reverse("incident-list"),
            {
                "title": "Categoría de otro tenant",
                "description": "No debe aceptarse.",
                "category_id": self.foreign_category.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Incident.objects.count(), 0)

    def test_student_can_only_read_own_incidents_and_history(self):
        own_incident = self.create_incident(reporter=self.student_a)
        other_incident = self.create_incident(reporter=self.student_b)
        self.client.force_authenticate(self.student_a)

        list_response = self.client.get(reverse("incident-list"))
        detail_response = self.client.get(
            reverse("incident-detail", args=[other_incident.pk])
        )
        history_response = self.client.get(
            reverse("incident-events", args=[own_incident.pk])
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual([item["id"] for item in list_response.data["results"]], [own_incident.pk])
        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(history_response.status_code, 200)

    def test_technician_sees_only_site_incidents_and_updates_only_assigned(self):
        assigned = self.create_incident(assigned_to=self.technician_a)
        unassigned = self.create_incident()
        foreign = Incident.objects.create(
            title="Incidencia externa",
            description="Fuera de la organización",
            organization=self.other_organization,
            category=self.foreign_category,
            location=self.foreign_location,
            reported_by=self.foreign_student,
            assigned_to=None,
        )
        self.client.force_authenticate(self.technician_a)

        list_response = self.client.get(reverse("incident-list"))
        forbidden_response = self.client.patch(
            reverse("incident-status", args=[unassigned.pk]),
            {"status": Incident.Status.IN_PROGRESS},
            format="json",
        )
        foreign_response = self.client.get(reverse("incident-detail", args=[foreign.pk]))
        allowed_response = self.client.patch(
            reverse("incident-status", args=[assigned.pk]),
            {"status": Incident.Status.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(
            {item["id"] for item in list_response.data["results"]},
            {assigned.pk, unassigned.pk},
        )
        self.assertEqual(forbidden_response.status_code, 403)
        self.assertEqual(foreign_response.status_code, 404)
        self.assertEqual(allowed_response.status_code, 200)
        self.assertEqual(assigned.events.get().event_type, IncidentEvent.EventType.STATUS_CHANGED)

    def test_admin_assignment_requires_technician_from_same_site(self):
        incident = self.create_incident()
        inactive_technician = get_user_model().objects.create_user(
            username="inactive_technician",
            email="inactive_technician@example.test",
            password="Secure-Test-Password-123",
            role=get_user_model().Role.TECHNICIAN,
            location=self.location_a,
            is_active=False,
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            location=self.location_a,
            user=inactive_technician,
            role=OrganizationMembership.Role.TECHNICIAN,
            is_active=False,
        )
        self.client.force_authenticate(self.admin)

        invalid_response = self.client.patch(
            reverse("incident-assign", args=[incident.pk]),
            {"assigned_to": self.technician_b.pk},
            format="json",
        )
        inactive_response = self.client.patch(
            reverse("incident-assign", args=[incident.pk]),
            {"assigned_to": inactive_technician.pk},
            format="json",
        )
        self.assertIsNone(incident.__class__.objects.get(pk=incident.pk).assigned_to)

        valid_response = self.client.patch(
            reverse("incident-assign", args=[incident.pk]),
            {"assigned_to": self.technician_a.pk},
            format="json",
        )
        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(inactive_response.status_code, 400)
        self.assertEqual(valid_response.status_code, 200)
        incident.refresh_from_db()
        self.assertEqual(incident.assigned_to, self.technician_a)
        self.assertEqual(incident.events.get().event_type, IncidentEvent.EventType.ASSIGNED)

    def test_admin_closes_resolved_incident_and_records_event(self):
        incident = self.create_incident(status=Incident.Status.RESOLVED)
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            reverse("incident-status", args=[incident.pk]),
            {"status": Incident.Status.CLOSED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        incident.refresh_from_db()
        self.assertEqual(incident.status, Incident.Status.CLOSED)
        event = incident.events.get()
        self.assertEqual(event.old_value, {"status": Incident.Status.RESOLVED})
        self.assertEqual(event.new_value, {"status": Incident.Status.CLOSED})

    def test_admin_reopens_closed_incident_and_records_event(self):
        incident = self.create_incident(status=Incident.Status.CLOSED)
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            reverse("incident-status", args=[incident.pk]),
            {"status": Incident.Status.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        incident.refresh_from_db()
        self.assertEqual(incident.status, Incident.Status.IN_PROGRESS)
        event = incident.events.get()
        self.assertEqual(event.old_value, {"status": Incident.Status.CLOSED})
        self.assertEqual(event.new_value, {"status": Incident.Status.IN_PROGRESS})

    def test_technician_cannot_skip_status_transition(self):
        incident = self.create_incident(assigned_to=self.technician_a)
        self.client.force_authenticate(self.technician_a)

        response = self.client.patch(
            reverse("incident-status", args=[incident.pk]),
            {"status": Incident.Status.RESOLVED},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        incident.refresh_from_db()
        self.assertEqual(incident.status, Incident.Status.PENDING)
        self.assertEqual(incident.events.count(), 0)

    def test_admin_can_filter_incidents_by_location(self):
        incident_a = self.create_incident()
        incident_b = self.create_incident(
            reporter=self.student_b,
            location=self.location_b,
        )
        self.client.force_authenticate(self.admin)

        all_response = self.client.get(reverse("incident-list"))
        filtered_response = self.client.get(
            reverse("incident-list"),
            {"location": self.location_b.pk},
        )

        self.assertEqual(
            {item["id"] for item in all_response.data["results"]},
            {incident_a.pk, incident_b.pk},
        )
        self.assertEqual(
            [item["id"] for item in filtered_response.data["results"]],
            [incident_b.pk],
        )

    def test_admin_can_filter_incidents_by_priority_and_category(self):
        urgent = self.create_incident()
        urgent.priority = Incident.Priority.CRITICAL
        urgent.save(update_fields=["priority"])
        other_category = Category.objects.create(
            organization=self.organization,
            name="Infraestructura",
        )
        priority_only = self.create_incident(reporter=self.student_b)
        category_only = self.create_incident()
        category_only.category = other_category
        category_only.priority = Incident.Priority.CRITICAL
        category_only.save(update_fields=["category", "priority"])
        self.client.force_authenticate(self.admin)

        filtered_response = self.client.get(
            reverse("incident-list"),
            {
                "priority": Incident.Priority.CRITICAL,
                "category": self.category.pk,
            },
        )
        priority_response = self.client.get(
            reverse("incident-list"),
            {"priority": Incident.Priority.CRITICAL},
        )
        category_response = self.client.get(
            reverse("incident-list"),
            {"category": self.category.pk},
        )
        foreign_category_response = self.client.get(
            reverse("incident-list"),
            {"category": self.foreign_category.pk},
        )

        self.assertEqual(filtered_response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in filtered_response.data["results"]],
            [urgent.pk],
        )
        self.assertEqual(
            {item["id"] for item in priority_response.data["results"]},
            {urgent.pk, category_only.pk},
        )
        self.assertEqual(
            {item["id"] for item in category_response.data["results"]},
            {urgent.pk, priority_only.pk},
        )
        self.assertEqual(foreign_category_response.status_code, 200)
        self.assertEqual(foreign_category_response.data["count"], 0)

    def test_organization_admin_cannot_access_another_organizations_resources(self):
        foreign_incident = Incident.objects.create(
            title="Incidencia externa",
            description="Fuera del tenant",
            organization=self.other_organization,
            category=self.foreign_category,
            location=self.foreign_location,
            reported_by=self.foreign_student,
        )
        self.client.force_authenticate(self.admin)

        detail_response = self.client.get(
            reverse("incident-detail", args=[foreign_incident.pk])
        )
        filtered_response = self.client.get(
            reverse("incident-list"),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )
        assignment_response = self.client.patch(
            reverse("incident-assign", args=[foreign_incident.pk]),
            {"assigned_to": None},
            format="json",
        )

        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(filtered_response.status_code, 403)
        self.assertEqual(assignment_response.status_code, 404)

    def test_superadmin_can_read_across_organizations(self):
        foreign_incident = Incident.objects.create(
            title="Incidencia externa",
            description="Fuera del tenant",
            organization=self.other_organization,
            category=self.foreign_category,
            location=self.foreign_location,
            reported_by=self.foreign_student,
        )
        self.client.force_authenticate(self.superadmin)

        list_response = self.client.get(reverse("incident-list"))
        detail_response = self.client.get(
            reverse("incident-detail", args=[foreign_incident.pk])
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertIn(foreign_incident.pk, {item["id"] for item in list_response.data["results"]})
        self.assertEqual(detail_response.status_code, 200)

    def test_emergencies_are_filtered_by_site(self):
        protocol_a = EmergencyProtocol.objects.create(
            location=self.location_a,
            title="Evacuación",
            content="Siga las rutas señalizadas.",
            contact_phone="123",
        )
        protocol_b = EmergencyProtocol.objects.create(
            location=self.location_b,
            title="Incendio",
            content="Aléjese del área.",
            contact_phone="456",
        )
        self.client.force_authenticate(self.student_a)

        response = self.client.get(reverse("emergency-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [protocol_a.pk])

        self.client.force_authenticate(self.admin)
        admin_all_response = self.client.get(reverse("emergency-list"))
        admin_site_response = self.client.get(
            reverse("emergency-list"),
            {"location": self.location_b.pk},
        )

        self.assertEqual(admin_all_response.data["count"], 2)
        self.assertEqual(
            [item["id"] for item in admin_site_response.data["results"]],
            [protocol_b.pk],
        )

    def test_non_admin_cannot_filter_incidents_by_another_site(self):
        self.client.force_authenticate(self.technician_a)

        response = self.client.get(
            reverse("incident-list"),
            {"location": self.location_b.pk},
        )

        self.assertEqual(response.status_code, 403)


class EmergencyAlertApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.organization = Organization.objects.create(
            name="Organización de alertas",
            slug="alert-test",
        )
        self.foreign_organization = Organization.objects.create(
            name="Organización ajena",
            slug="alert-foreign-test",
        )
        self.location = Location.objects.create(
            organization=self.organization,
            name="Sede de alertas",
            code="ALERT",
        )
        self.foreign_location = Location.objects.create(
            organization=self.foreign_organization,
            name="Sede ajena",
            code="FOREIGN",
        )
        self.admin = user_model.objects.create_user(
            username="alert_admin",
            email="alert_admin@example.test",
            password="test-password",
            role=user_model.Role.ADMIN,
        )
        self.member = user_model.objects.create_user(
            username="alert_member",
            email="alert_member@example.test",
            password="test-password",
            role=user_model.Role.STUDENT,
            location=self.location,
        )
        self.foreign_admin = user_model.objects.create_user(
            username="foreign_alert_admin",
            email="foreign_alert_admin@example.test",
            password="test-password",
            role=user_model.Role.ADMIN,
        )
        self.foreign_member = user_model.objects.create_user(
            username="foreign_alert_member",
            email="foreign_alert_member@example.test",
            password="test-password",
            role=user_model.Role.STUDENT,
            location=self.foreign_location,
        )
        for organization, user, location, role in (
            (
                self.organization,
                self.admin,
                None,
                OrganizationMembership.Role.ADMIN,
            ),
            (
                self.organization,
                self.member,
                self.location,
                OrganizationMembership.Role.USER,
            ),
            (
                self.foreign_organization,
                self.foreign_admin,
                None,
                OrganizationMembership.Role.ADMIN,
            ),
            (
                self.foreign_organization,
                self.foreign_member,
                self.foreign_location,
                OrganizationMembership.Role.USER,
            ),
        ):
            OrganizationMembership.objects.create(
                organization=organization,
                user=user,
                location=location,
                role=role,
            )
        self.admin_device = PushDevice.objects.create(
            user=self.admin,
            expo_push_token="ExponentPushToken[alert-admin]",
            platform=PushDevice.Platform.ANDROID,
        )
        self.member_device = PushDevice.objects.create(
            user=self.member,
            expo_push_token="ExponentPushToken[alert-member]",
            platform=PushDevice.Platform.IOS,
        )
        self.foreign_device = PushDevice.objects.create(
            user=self.foreign_member,
            expo_push_token="ExponentPushToken[foreign-member]",
            platform=PushDevice.Platform.ANDROID,
        )

    def test_only_organization_admin_can_issue_alerts_to_active_tenant_devices(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("emergency-alert-list"),
            {"title": "Evacuación", "message": "Diríjanse al punto seguro."},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        alert = EmergencyAlert.objects.get()
        self.assertEqual(alert.organization, self.organization)
        self.assertEqual(
            set(alert.deliveries.values_list("device_id", flat=True)),
            {self.admin_device.pk, self.member_device.pk},
        )
        self.assertEqual(response.data["pending_deliveries"], 2)

        self.client.force_authenticate(self.member)
        denied_response = self.client.post(
            reverse("emergency-alert-list"),
            {"title": "No autorizada", "message": "Mensaje."},
            format="json",
        )

        self.assertEqual(denied_response.status_code, 403)
        self.assertEqual(EmergencyAlert.objects.count(), 1)

    def test_cancel_stops_pending_alerts_and_queues_cancellation_once(self):
        alert = EmergencyAlert.objects.create(
            organization=self.organization,
            title="Prueba",
            message="Aviso.",
            created_by=self.admin,
        )
        EmergencyAlertDelivery.objects.bulk_create(
            [
                EmergencyAlertDelivery(
                    alert=alert,
                    device=device,
                    kind=EmergencyAlertDelivery.Kind.ALERT,
                )
                for device in (self.admin_device, self.member_device)
            ]
        )
        self.client.force_authenticate(self.admin)

        first_response = self.client.post(
            reverse("emergency-alert-cancel", args=[alert.pk]),
        )
        repeated_response = self.client.post(
            reverse("emergency-alert-cancel", args=[alert.pk]),
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(repeated_response.status_code, 200)
        self.assertEqual(first_response.data["status"], EmergencyAlert.Status.CANCELLED)
        self.assertEqual(
            alert.deliveries.filter(
                kind=EmergencyAlertDelivery.Kind.ALERT,
                status=EmergencyAlertDelivery.Status.CANCELLED,
            ).count(),
            2,
        )
        self.assertEqual(
            alert.deliveries.filter(
                kind=EmergencyAlertDelivery.Kind.CANCELLATION,
                status=EmergencyAlertDelivery.Status.PENDING,
            ).count(),
            2,
        )

    def test_alert_list_is_scoped_to_the_active_organization(self):
        alert = EmergencyAlert.objects.create(
            organization=self.foreign_organization,
            title="Privada",
            message="No debe verse.",
            created_by=self.foreign_admin,
        )
        self.client.force_authenticate(self.admin)

        response = self.client.get(reverse("emergency-alert-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertNotIn(alert.pk, {item["id"] for item in response.data["results"]})

    def test_non_admin_cannot_cancel_an_alert(self):
        alert = EmergencyAlert.objects.create(
            organization=self.organization,
            title="Activa",
            message="Aviso.",
            created_by=self.admin,
        )
        self.client.force_authenticate(self.member)

        response = self.client.post(
            reverse("emergency-alert-cancel", args=[alert.pk]),
        )

        self.assertEqual(response.status_code, 403)
        alert.refresh_from_db()
        self.assertEqual(alert.status, EmergencyAlert.Status.ACTIVE)
        self.assertEqual(alert.deliveries.count(), 0)

    def test_push_device_token_cannot_be_claimed_by_another_account(self):
        self.client.force_authenticate(self.member)

        response = self.client.post(
            reverse("push-device-register"),
            {
                "expo_push_token": self.admin_device.expo_push_token,
                "platform": PushDevice.Platform.ANDROID,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403, response.data)
        self.admin_device.refresh_from_db()
        self.assertEqual(self.admin_device.user, self.admin)

    def test_device_owner_can_disable_push_registration(self):
        self.client.force_authenticate(self.admin)

        response = self.client.delete(
            reverse("push-device-detail", args=[self.admin_device.pk]),
        )

        self.assertEqual(response.status_code, 204)
        self.admin_device.refresh_from_db()
        self.assertFalse(self.admin_device.is_active)

    def test_device_owner_can_refresh_existing_registration(self):
        self.admin_device.is_active = False
        self.admin_device.save(update_fields=["is_active"])
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse("push-device-register"),
            {
                "expo_push_token": self.admin_device.expo_push_token,
                "platform": PushDevice.Platform.ANDROID,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.admin_device.refresh_from_db()
        self.assertTrue(self.admin_device.is_active)
        self.assertEqual(PushDevice.objects.count(), 3)


class EmergencyAlertDeliveryCommandTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.organization = Organization.objects.create(
            name="Servicio push",
            slug="push-command-test",
        )
        self.admin = user_model.objects.create_user(
            username="push_admin",
            email="push_admin@example.test",
            password="test-password",
            role=user_model.Role.ADMIN,
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.admin,
            role=OrganizationMembership.Role.ADMIN,
        )
        alert = EmergencyAlert.objects.create(
            organization=self.organization,
            title="Prueba push",
            message="Mensaje de prueba.",
            created_by=self.admin,
        )
        device = PushDevice.objects.create(
            user=self.admin,
            expo_push_token="ExponentPushToken[worker]",
            platform=PushDevice.Platform.ANDROID,
        )
        self.delivery = EmergencyAlertDelivery.objects.create(
            alert=alert,
            device=device,
            kind=EmergencyAlertDelivery.Kind.ALERT,
        )

    @patch("incidents.management.commands.send_emergency_alerts.urlopen")
    def test_worker_accepts_push_without_claiming_device_delivery(self, mock_urlopen):
        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = b'{"data":[{"status":"ok","id":"ticket"}]}'

        call_command("send_emergency_alerts")

        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, EmergencyAlertDelivery.Status.ACCEPTED)
        self.assertEqual(self.delivery.attempts, 1)
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch(
        "incidents.management.commands.send_emergency_alerts.urlopen",
        side_effect=URLError("servicio fuera de línea"),
    )
    def test_worker_stops_after_three_attempts(self, mock_urlopen):
        for attempt in range(3):
            self.delivery.next_attempt_at = timezone.now()
            self.delivery.save(update_fields=["next_attempt_at"])
            call_command("send_emergency_alerts")
            self.delivery.refresh_from_db()
            if attempt < 2:
                self.assertEqual(
                    self.delivery.status,
                    EmergencyAlertDelivery.Status.PENDING,
                )

        self.assertEqual(self.delivery.status, EmergencyAlertDelivery.Status.FAILED)
        self.assertEqual(self.delivery.attempts, 3)
        self.assertEqual(mock_urlopen.call_count, 3)

    @patch("incidents.management.commands.send_emergency_alerts.urlopen")
    def test_worker_surfaces_receipt_failures_and_disables_invalid_device(self, mock_urlopen):
        self.delivery.status = EmergencyAlertDelivery.Status.ACCEPTED
        self.delivery.provider_ticket_id = "ticket-123"
        self.delivery.receipt_due_at = timezone.now()
        self.delivery.save(
            update_fields=["status", "provider_ticket_id", "receipt_due_at"]
        )
        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = (
            b'{"data":{"ticket-123":{"status":"error","message":"Token inv\\u00e1lido",'
            b'"details":{"error":"DeviceNotRegistered"}}}}'
        )

        call_command("send_emergency_alerts")

        self.delivery.refresh_from_db()
        self.delivery.device.refresh_from_db()
        self.assertEqual(self.delivery.status, EmergencyAlertDelivery.Status.FAILED)
        self.assertIsNotNone(self.delivery.receipt_checked_at)
        self.assertFalse(self.delivery.device.is_active)
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("emergency-alert-list"))
        self.assertIn("DeviceNotRegistered", response.data["results"][0]["delivery_errors"][0])
