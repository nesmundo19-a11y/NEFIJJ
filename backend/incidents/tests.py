from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import Location, Organization, OrganizationMembership
from .models import Category, EmergencyProtocol, Incident, IncidentEvent


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
