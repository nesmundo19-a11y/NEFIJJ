import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import (
    Location,
    Organization,
    OrganizationMembership,
)
from incidents.models import Category, EmergencyProtocol, Incident, IncidentEvent


class Command(BaseCommand):
    help = "Create isolated demo data; optionally enable temporary demo logins."

    def add_arguments(self, parser):
        parser.add_argument(
            "--enable-login",
            action="store_true",
            help="Set one random password for all demo accounts and print it once.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if (
            not settings.DEBUG
            or not getattr(settings, "NEFIJJ_DEMO_MODE", False)
            or settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3"
        ):
            raise CommandError(
                "seed_demo only runs with config.demo_settings and its isolated SQLite database."
            )

        User = get_user_model()
        demo_password = secrets.token_urlsafe(18) if options["enable_login"] else None
        admin = self._get_demo_superadmin(User, demo_password)

        demo_organization = self._get_demo_organization()
        locations = {
            code: self._get_demo_location(demo_organization, code, name)
            for code, name in (
                ("DEMO-A", "Sede Demo A"),
                ("DEMO-B", "Sede Demo B"),
            )
        }
        category = self._get_demo_category(demo_organization)
        self._get_demo_organization_admin(User, demo_organization, demo_password)

        students = {
            "A": self._get_demo_user(
                User, "demo_estudiante_a", "demo.estudiante.a@example.test",
                User.Role.STUDENT, locations["DEMO-A"], demo_organization, demo_password,
            ),
            "B": self._get_demo_user(
                User, "demo_estudiante_b", "demo.estudiante.b@example.test",
                User.Role.STUDENT, locations["DEMO-B"], demo_organization, demo_password,
            ),
        }
        technicians = {
            "A": self._get_demo_user(
                User, "demo_tecnico_a", "demo.tecnico.a@example.test",
                User.Role.TECHNICIAN, locations["DEMO-A"], demo_organization, demo_password,
            ),
            "B": self._get_demo_user(
                User, "demo_tecnico_b", "demo.tecnico.b@example.test",
                User.Role.TECHNICIAN, locations["DEMO-B"], demo_organization, demo_password,
            ),
        }

        for location in locations.values():
            EmergencyProtocol.objects.get_or_create(
                location=location,
                title="DEMO - Protocolo de prueba",
                defaults={
                    "content": (
                        "Contenido ficticio para probar la aplicación. "
                        "No es un protocolo operativo real."
                    ),
                    "contact_phone": "DEMO - SIN CONTACTO",
                },
            )

        scenarios = (
            ("DEMO - Incidencia pendiente sede A", "A", Incident.Status.PENDING, None),
            (
                "DEMO - Incidencia en proceso sede A",
                "A",
                Incident.Status.IN_PROGRESS,
                "A",
            ),
            ("DEMO - Incidencia resuelta sede A", "A", Incident.Status.RESOLVED, "A"),
            ("DEMO - Incidencia cerrada sede A", "A", Incident.Status.CLOSED, "A"),
            ("DEMO - Incidencia pendiente sede B", "B", Incident.Status.PENDING, None),
        )
        for title, site_key, status, technician_key in scenarios:
            student = students[site_key]
            location = locations[f"DEMO-{site_key}"]
            technician = technicians[technician_key] if technician_key else None
            incident, created = Incident.objects.get_or_create(
                title=title,
                location=location,
                defaults={
                    "description": (
                        "Registro ficticio de demostración; no corresponde a una "
                        "incidencia real."
                    ),
                    "status": status,
                    "priority": Incident.Priority.MEDIUM,
                    "organization": demo_organization,
                    "category": category,
                    "reported_by": student,
                    "assigned_to": technician,
                },
            )
            if created:
                self._create_demo_events(incident, student, technician, admin)

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data is ready: 2 locations, 1 organization admin, "
                "2 users, 2 technicians, "
                "1 category, 2 protocols, and 5 incidents."
            )
        )
        if demo_password:
            self.stdout.write(
                "Demo accounts: demo_superadmin, demo_admin, demo_estudiante_a, "
                "demo_estudiante_b, demo_tecnico_a, demo_tecnico_b"
            )
            self.stdout.write(f"Temporary shared demo password: {demo_password}")
            self.stdout.write("Run this command again with --enable-login to rotate it.")

    @staticmethod
    def _get_demo_superadmin(User, password):
        username = "demo_superadmin"
        email = "demo.superadmin@example.test"
        user = User.objects.filter(username=username).first()
        if user is None:
            if User.objects.filter(email=email).exists():
                raise CommandError(f"Demo email {email} is already in use.")
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )
        elif (
            user.email != email
            or not user.is_superuser
            or not user.is_active
        ):
            raise CommandError(f"Existing demo account {username} is incompatible.")

        if password and user.check_password(password) is False:
            user.set_password(password)
            user.save(update_fields=["password"])
        elif not password and not user.has_usable_password():
            return user
        return user

    @staticmethod
    def _get_demo_organization():
        organization, _ = Organization.objects.get_or_create(
            slug="nefijj-demo",
            defaults={"name": "NEFIJJ - Datos DEMO"},
        )
        if organization.name != "NEFIJJ - Datos DEMO" or not organization.is_active:
            raise CommandError("Existing DEMO organization is incompatible.")
        return organization

    @staticmethod
    def _get_demo_location(organization, code, name):
        location, _ = Location.objects.get_or_create(
            code=code,
            defaults={"name": name, "organization": organization},
        )
        if (
            location.name != name
            or not location.is_active
            or location.organization_id != organization.pk
        ):
            raise CommandError(f"Existing demo location {code} is incompatible.")
        return location

    @staticmethod
    def _get_demo_category(organization):
        category, _ = Category.objects.get_or_create(
            organization=organization,
            name="DEMO - Infraestructura",
            defaults={"description": "Categoría ficticia para pruebas."},
        )
        if not category.is_active:
            raise CommandError("Existing demo category is inactive.")
        return category

    @staticmethod
    def _get_demo_user(
        User,
        username,
        email,
        role,
        location,
        organization,
        password,
    ):
        user = User.objects.filter(username=username).first()
        if user is not None:
            if (
                user.email != email
                or user.role != role
                or user.location_id != location.pk
                or user.is_superuser
                or not user.is_active
            ):
                raise CommandError(f"Existing demo account {username} is incompatible.")
            membership, _ = OrganizationMembership.objects.get_or_create(
                organization=organization,
                user=user,
                defaults={
                    "location": location,
                    "role": (
                        OrganizationMembership.Role.TECHNICIAN
                        if role == User.Role.TECHNICIAN
                        else OrganizationMembership.Role.USER
                    ),
                    "is_active": user.is_active,
                },
            )
            if (
                membership.location_id != location.pk
                or membership.role
                != (
                    OrganizationMembership.Role.TECHNICIAN
                    if role == User.Role.TECHNICIAN
                    else OrganizationMembership.Role.USER
                )
            ):
                raise CommandError(f"Existing demo membership {username} is incompatible.")
            if password:
                user.set_password(password)
                user.save(update_fields=["password"])
            return user

        if User.objects.filter(email=email).exists():
            raise CommandError(f"Demo email {email} is already in use.")

        user = User(
            username=username,
            email=email,
            role=role,
            location=location,
            is_active=True,
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        OrganizationMembership.objects.create(
            organization=organization,
            location=location,
            user=user,
            role=(
                OrganizationMembership.Role.TECHNICIAN
                if role == User.Role.TECHNICIAN
                else OrganizationMembership.Role.USER
            ),
            is_active=True,
        )
        return user

    @staticmethod
    def _get_demo_organization_admin(User, organization, password):
        username = "demo_admin"
        email = "demo.admin@example.test"
        user = User.objects.filter(username=username).first()
        if user is None:
            if User.objects.filter(email=email).exists():
                raise CommandError(f"Demo email {email} is already in use.")
            user = User(
                username=username,
                email=email,
                role=User.Role.ADMIN,
                is_active=True,
            )
            if password:
                user.set_password(password)
            else:
                user.set_unusable_password()
            user.save()
        elif (
            user.email != email
            or user.role != User.Role.ADMIN
            or user.is_superuser
            or not user.is_active
        ):
            raise CommandError(f"Existing demo account {username} is incompatible.")
        elif password:
            user.set_password(password)
            user.save(update_fields=["password"])

        membership, _ = OrganizationMembership.objects.get_or_create(
            organization=organization,
            user=user,
            defaults={
                "role": OrganizationMembership.Role.ADMIN,
                "is_active": user.is_active,
            },
        )
        if membership.role != OrganizationMembership.Role.ADMIN or not membership.is_active:
            raise CommandError(f"Existing demo membership {username} is incompatible.")
        return user

    @staticmethod
    def _create_demo_events(incident, student, technician, admin):
        IncidentEvent.objects.create(
            incident=incident,
            actor=student,
            event_type=IncidentEvent.EventType.CREATED,
            new_value={"status": Incident.Status.PENDING},
        )
        if technician is not None:
            IncidentEvent.objects.create(
                incident=incident,
                actor=admin,
                event_type=IncidentEvent.EventType.ASSIGNED,
                old_value={"assigned_to": None},
                new_value={"assigned_to": technician.pk},
            )

        status_events = {
            Incident.Status.IN_PROGRESS: (
                (Incident.Status.PENDING, Incident.Status.IN_PROGRESS, technician),
            ),
            Incident.Status.RESOLVED: (
                (Incident.Status.PENDING, Incident.Status.IN_PROGRESS, technician),
                (Incident.Status.IN_PROGRESS, Incident.Status.RESOLVED, technician),
            ),
            Incident.Status.CLOSED: (
                (Incident.Status.PENDING, Incident.Status.IN_PROGRESS, technician),
                (Incident.Status.IN_PROGRESS, Incident.Status.RESOLVED, technician),
                (Incident.Status.RESOLVED, Incident.Status.CLOSED, admin),
            ),
        }
        for old_status, new_status, actor in status_events.get(incident.status, ()):
            IncidentEvent.objects.create(
                incident=incident,
                actor=actor,
                event_type=IncidentEvent.EventType.STATUS_CHANGED,
                old_value={"status": old_status},
                new_value={"status": new_status},
            )
