from io import StringIO
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.db import connection
from django.urls import reverse
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.utils import timezone
from django.db.migrations.executor import MigrationExecutor
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.test import APITestCase

from incidents.models import Category, EmergencyProtocol, Incident

from .invitations import add_colombia_business_days
from .models import (
    Location,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
)


class ColombiaBusinessDayTests(SimpleTestCase):
    def test_expiry_skips_weekends_and_colombian_holidays(self):
        timezone = ZoneInfo("America/Bogota")
        start_at = datetime(2026, 12, 18, 15, 30, tzinfo=timezone)

        expiry = add_colombia_business_days(start_at, 7)

        self.assertEqual(expiry, datetime(2026, 12, 30, 15, 30, tzinfo=timezone))

    def test_expiry_preserves_colombian_local_time_from_utc_input(self):
        start_at = datetime(2026, 12, 18, 20, 30, tzinfo=ZoneInfo("UTC"))

        expiry = add_colombia_business_days(start_at, 7)

        self.assertEqual(
            expiry,
            datetime(2026, 12, 30, 15, 30, tzinfo=ZoneInfo("America/Bogota")),
        )

    def test_expiry_rejects_naive_start_and_negative_days(self):
        with self.assertRaises(ValueError):
            add_colombia_business_days(datetime(2026, 12, 18, 15, 30), 7)
        with self.assertRaises(ValueError):
            add_colombia_business_days(
                datetime(2026, 12, 18, 15, 30, tzinfo=ZoneInfo("America/Bogota")),
                -1,
            )


class AuthenticationApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.organization = Organization.objects.create(
            name="Organización de prueba",
            slug="auth-test",
        )
        self.location = Location.objects.create(
            organization=self.organization,
            name="Sede de prueba",
            code="TEST",
        )
        self.user = user_model.objects.create_user(
            username="student",
            email="student@example.test",
            password="Secure-Test-Password-123",
            role=user_model.Role.STUDENT,
            location=self.location,
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            location=self.location,
            user=self.user,
            role=OrganizationMembership.Role.USER,
        )

    def test_login_returns_jwt_and_user_scope(self):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "student", "password": "Secure-Test-Password-123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["role"], "user")
        self.assertEqual(response.data["user"]["location_id"], self.location.pk)
        self.assertEqual(
            response.data["user"]["organizations"][0]["organization_id"],
            self.organization.pk,
        )

    def test_invalid_login_is_rejected(self):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "student", "password": "incorrect"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_access_token_can_be_refreshed(self):
        login = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "student", "password": "Secure-Test-Password-123"},
            format="json",
        )

        response = self.client.post(
            reverse("token_refresh"),
            {"refresh": login.data["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)

    def test_expired_access_token_cannot_access_protected_endpoint(self):
        token = AccessToken.for_user(self.user)
        token.set_exp(lifetime=timedelta(seconds=-1))

        response = self.client.get(
            reverse("incident-list"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 401)

    def test_superuser_is_created_with_admin_role(self):
        user = get_user_model().objects.create_superuser(
            username="root_admin",
            email="root_admin@example.test",
            password="Secure-Test-Password-123",
        )

        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, get_user_model().Role.SUPERADMIN)
        self.assertIsNone(user.location_id)

    def test_user_password_change_invalidates_existing_access_and_refresh_tokens(self):
        login = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "student", "password": "Secure-Test-Password-123"},
            format="json",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}",
        )

        response = self.client.post(
            reverse("password-change"),
            {
                "old_password": "Secure-Test-Password-123",
                "new_password": "Different-Secure-Password-456",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 204)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Different-Secure-Password-456"))
        protected_response = self.client.get(reverse("my-organizations"))
        refresh_response = self.client.post(
            reverse("token_refresh"),
            {"refresh": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(protected_response.status_code, 401)
        self.assertEqual(refresh_response.status_code, 401)

    def test_password_change_rejects_wrong_current_and_reused_password(self):
        self.client.force_authenticate(self.user)

        wrong_current = self.client.post(
            reverse("password-change"),
            {
                "old_password": "wrong-current-password",
                "new_password": "Different-Secure-Password-456",
            },
            format="json",
        )
        reused_password = self.client.post(
            reverse("password-change"),
            {
                "old_password": "Secure-Test-Password-123",
                "new_password": "Secure-Test-Password-123",
            },
            format="json",
        )

        self.assertEqual(wrong_current.status_code, 400)
        self.assertEqual(reused_password.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Secure-Test-Password-123"))


class AdminAccountApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.organization = Organization.objects.create(
            name="Organización administrativa",
            slug="account-admin-test",
        )
        self.location = Location.objects.create(
            organization=self.organization,
            name="Sede administrativa",
            code="ADMIN-LOC",
        )
        self.admin = user_model.objects.create_user(
            username="global_admin",
            email="global_admin@example.test",
            password="Secure-Test-Password-123",
            role=user_model.Role.ADMIN,
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.admin,
            role=OrganizationMembership.Role.ADMIN,
        )
        self.student = user_model.objects.create_user(
            username="regular_student",
            email="regular_student@example.test",
            password="Secure-Test-Password-123",
            role=user_model.Role.STUDENT,
            location=self.location,
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            location=self.location,
            user=self.student,
            role=OrganizationMembership.Role.USER,
        )

    def test_admin_can_create_user_with_hashed_password(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse("user-list"),
            {
                "username": "new_technician",
                "first_name": "Nueva",
                "last_name": "Técnica",
                "email": "new_technician@example.test",
                "password": "J9#rVm2!xQa7Lp4",
                "role": "technician",
                "location_id": self.location.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        created_user = get_user_model().objects.get(username="new_technician")
        self.assertTrue(created_user.check_password("J9#rVm2!xQa7Lp4"))
        self.assertEqual(created_user.first_name, "Nueva")
        self.assertEqual(created_user.last_name, "Técnica")
        self.assertTrue(
            OrganizationMembership.objects.filter(
                organization=self.organization,
                user=created_user,
                location=self.location,
                role=OrganizationMembership.Role.TECHNICIAN,
            ).exists()
        )
        self.assertNotIn("password", response.data)

    def test_admin_cannot_change_another_users_password_through_user_patch(self):
        self.client.force_authenticate(self.admin)
        original_password_hash = self.student.password

        response = self.client.patch(
            reverse("user-detail", args=[self.student.pk]),
            {"password": "Different-Secure-Password-456"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.student.refresh_from_db()
        self.assertEqual(self.student.password, original_password_hash)

    def test_non_admin_cannot_manage_users_or_locations(self):
        self.client.force_authenticate(self.student)

        users_response = self.client.get(reverse("user-list"))
        locations_response = self.client.get(reverse("location-list"))

        self.assertEqual(users_response.status_code, 403)
        self.assertEqual(locations_response.status_code, 403)

    def test_demo_seed_is_safe_to_run_more_than_once(self):
        user_model = get_user_model()
        output = StringIO()
        with override_settings(DEBUG=True, NEFIJJ_DEMO_MODE=True):
            call_command("seed_demo", stdout=StringIO())
            call_command("seed_demo", "--enable-login", stdout=output)

        self.assertEqual(Location.objects.filter(code__startswith="DEMO-").count(), 2)
        self.assertEqual(Category.objects.filter(name__startswith="DEMO -").count(), 1)
        self.assertEqual(
            user_model.objects.filter(username__startswith="demo_").count(),
            6,
        )
        self.assertEqual(EmergencyProtocol.objects.filter(title__startswith="DEMO -").count(), 2)
        self.assertEqual(Incident.objects.filter(title__startswith="DEMO -").count(), 5)
        self.assertTrue(all(
            user.has_usable_password()
            for user in user_model.objects.filter(username__startswith="demo_")
        ))
        password_line = next(
            line for line in output.getvalue().splitlines()
            if line.startswith("Temporary shared demo password: ")
        )
        password = password_line.partition(": ")[2]
        self.assertTrue(user_model.objects.get(username="demo_superadmin").check_password(password))
        self.assertTrue(user_model.objects.get(username="demo_admin").check_password(password))
        self.assertTrue(user_model.objects.get(username="demo_estudiante_a").check_password(password))
        self.assertTrue(user_model.objects.get(username="demo_tecnico_a").check_password(password))

    def test_demo_seed_refuses_non_demo_settings(self):
        with override_settings(DEBUG=True, NEFIJJ_DEMO_MODE=False):
            with self.assertRaises(CommandError):
                call_command("seed_demo", stdout=StringIO())


class OrganizationApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.organization = Organization.objects.create(
            name="Universidad de La Guajira",
            slug="organization-api-test",
        )
        self.other_organization = Organization.objects.create(
            name="Organización DEMO",
            slug="organization-api-demo",
        )
        self.location = Location.objects.create(
            organization=self.organization,
            name="Sede real",
            code="ORG-REAL",
        )
        self.other_location = Location.objects.create(
            organization=self.other_organization,
            name="Sede demo",
            code="ORG-DEMO",
        )
        self.admin = user_model.objects.create_user(
            username="organization_admin",
            email="organization_admin@example.test",
            password="Secure-Test-Password-123",
            role=user_model.Role.ADMIN,
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.admin,
            role=OrganizationMembership.Role.ADMIN,
        )
        self.member = user_model.objects.create_user(
            username="organization_member",
            email="organization_member@example.test",
            password="Secure-Test-Password-123",
            role=user_model.Role.STUDENT,
            location=self.location,
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            location=self.location,
            user=self.member,
            role=OrganizationMembership.Role.USER,
        )
        self.superadmin = user_model.objects.create_superuser(
            username="platform_owner",
            email="platform_owner@example.test",
            password="Secure-Test-Password-123",
        )

    def test_only_superadmin_can_list_and_create_organizations(self):
        self.client.force_authenticate(self.admin)
        denied = self.client.get(reverse("organization-list"))
        denied_status_update = self.client.patch(
            reverse("organization-status", args=[self.organization.pk]),
            {"status": Organization.Status.SUSPENDED},
            format="json",
        )

        self.client.force_authenticate(self.superadmin)
        allowed = self.client.get(reverse("organization-list"))
        created = self.client.post(
            reverse("organization-list"),
            {"name": "Nueva organización", "slug": "new-organization"},
            format="json",
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied_status_update.status_code, 403)
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.status, Organization.Status.ACTIVE)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(created.status_code, 201)

    def test_superadmin_organization_list_includes_global_status_counts(self):
        self.other_organization.status = Organization.Status.SUSPENDED
        self.other_organization.save(update_fields=["status"])
        self.client.force_authenticate(self.superadmin)

        response = self.client.get(reverse("organization-list"))

        self.assertEqual(response.status_code, 200)
        expected_summary = {
            "total": Organization.objects.count(),
            "active": Organization.objects.filter(
                status=Organization.Status.ACTIVE
            ).count(),
            "suspended": Organization.objects.filter(
                status=Organization.Status.SUSPENDED
            ).count(),
        }
        self.assertEqual(
            response.data["summary"],
            expected_summary,
        )
        self.assertEqual(response.data["count"], expected_summary["total"])

        status_response = self.client.patch(
            reverse("organization-status", args=[self.organization.pk]),
            {"status": Organization.Status.SUSPENDED},
            format="json",
        )
        refreshed_response = self.client.get(reverse("organization-list"))

        self.assertEqual(status_response.status_code, 200)
        expected_summary["active"] -= 1
        expected_summary["suspended"] += 1
        self.assertEqual(
            refreshed_response.data["summary"],
            expected_summary,
        )

    def test_organization_admin_cannot_manage_foreign_users_or_locations(self):
        self.client.force_authenticate(self.admin)
        headers = {"HTTP_X_ORGANIZATION_ID": str(self.other_organization.pk)}

        users_response = self.client.get(reverse("user-list"), **headers)
        locations_response = self.client.get(reverse("location-list"), **headers)

        self.assertEqual(users_response.status_code, 403)
        self.assertEqual(locations_response.status_code, 403)

    def test_invitation_is_hashed_expires_and_can_only_be_used_once(self):
        self.client.force_authenticate(self.superadmin)
        start_at = datetime(2026, 12, 18, 20, 30, tzinfo=ZoneInfo("UTC"))
        with patch("accounts.views.timezone.now", return_value=start_at):
            create_response = self.client.post(
                reverse(
                    "organization-invitations",
                    args=[self.other_organization.pk],
                ),
                HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
            )
        code = create_response.data["code"]
        invitation = OrganizationInvitation.objects.get(pk=create_response.data["id"])
        self.assertEqual(create_response.status_code, 201)
        self.assertNotEqual(invitation.token_hash, code)
        self.assertEqual(
            invitation.expires_at,
            datetime(2026, 12, 30, 20, 30, tzinfo=ZoneInfo("UTC")),
        )

        self.client.force_authenticate(self.member)
        join_response = self.client.post(
            reverse("membership-join"),
            {"code": code, "location_id": self.other_location.pk},
            format="json",
        )
        repeated_response = self.client.post(
            reverse("membership-join"),
            {"code": code, "location_id": self.other_location.pk},
            format="json",
        )

        self.assertEqual(join_response.status_code, 201)
        self.assertEqual(repeated_response.status_code, 400)
        missing_scope_response = self.client.get(reverse("incident-list"))
        selected_scope_response = self.client.get(
            reverse("incident-list"),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )
        self.assertEqual(missing_scope_response.status_code, 400)
        self.assertEqual(selected_scope_response.status_code, 200)
        membership = OrganizationMembership.objects.get(
            user=self.member,
            organization=self.other_organization,
        )
        self.assertEqual(membership.location, self.other_location)
        invitation.refresh_from_db()
        self.assertEqual(invitation.used_by, self.member)

    def test_invitation_preview_returns_active_locations_without_consuming_code(self):
        inactive_location = Location.objects.create(
            organization=self.other_organization,
            name="Sede inactiva",
            code="ORG-DEMO-OFF",
            is_active=False,
        )
        self.client.force_authenticate(self.superadmin)
        create_response = self.client.post(
            reverse("organization-invitations", args=[self.other_organization.pk]),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )

        self.client.force_authenticate(self.member)
        preview_response = self.client.post(
            reverse("invitation-preview"),
            {"code": create_response.data["code"]},
            format="json",
        )
        join_response = self.client.post(
            reverse("membership-join"),
            {"code": create_response.data["code"], "location_id": self.other_location.pk},
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(
            preview_response.data["locations"],
            [{"id": self.other_location.pk, "name": self.other_location.name}],
        )
        self.assertNotIn(inactive_location.pk, [
            location["id"] for location in preview_response.data["locations"]
        ])
        self.assertEqual(join_response.status_code, 201)

    def test_invitation_preview_rejects_revoked_and_expired_codes(self):
        self.client.force_authenticate(self.superadmin)
        revoked = self.client.post(
            reverse("organization-invitations", args=[self.other_organization.pk]),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )
        expired = self.client.post(
            reverse("organization-invitations", args=[self.other_organization.pk]),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )
        self.client.post(
            reverse(
                "organization-invitation-revoke",
                args=[self.other_organization.pk, revoked.data["id"]],
            ),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )
        OrganizationInvitation.objects.filter(pk=expired.data["id"]).update(
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        self.client.force_authenticate(self.member)
        revoked_response = self.client.post(
            reverse("invitation-preview"),
            {"code": revoked.data["code"]},
            format="json",
        )
        expired_response = self.client.post(
            reverse("invitation-preview"),
            {"code": expired.data["code"]},
            format="json",
        )

        self.assertEqual(revoked_response.status_code, 400)
        self.assertEqual(expired_response.status_code, 400)
        self.assertEqual(revoked_response.data["code"], expired_response.data["code"])

    def test_invitation_list_does_not_expose_codes_and_is_tenant_scoped(self):
        self.client.force_authenticate(self.superadmin)
        created = self.client.post(
            reverse("organization-invitations", args=[self.other_organization.pk]),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )

        listed = self.client.get(
            reverse("organization-invitations", args=[self.other_organization.pk]),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)
        self.assertEqual(listed.data[0]["id"], created.data["id"])
        self.assertNotIn("code", listed.data[0])

    def test_invitation_preview_requires_authentication(self):
        self.client.force_authenticate(self.superadmin)
        created = self.client.post(
            reverse("organization-invitations", args=[self.other_organization.pk]),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )
        self.client.force_authenticate(user=None)

        response = self.client.post(
            reverse("invitation-preview"),
            {"code": created.data["code"]},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_invitation_creation_requires_an_active_location(self):
        self.other_location.is_active = False
        self.other_location.save(update_fields=["is_active"])
        self.client.force_authenticate(self.superadmin)

        response = self.client.post(
            reverse("organization-invitations", args=[self.other_organization.pk]),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            OrganizationInvitation.objects.filter(
                organization=self.other_organization,
            ).exists()
        )

    def test_revoked_invitation_cannot_be_used(self):
        self.client.force_authenticate(self.superadmin)
        create_response = self.client.post(
            reverse(
                "organization-invitations",
                args=[self.other_organization.pk],
            ),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )
        revoke_response = self.client.post(
            reverse(
                "organization-invitation-revoke",
                args=[self.other_organization.pk, create_response.data["id"]],
            ),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )

        self.client.force_authenticate(self.member)
        join_response = self.client.post(
            reverse("membership-join"),
            {"code": create_response.data["code"], "location_id": self.other_location.pk},
            format="json",
        )

        self.assertEqual(revoke_response.status_code, 204)
        self.assertEqual(join_response.status_code, 400)
        self.assertFalse(
            OrganizationMembership.objects.filter(
                user=self.member,
                organization=self.other_organization,
            ).exists()
        )

    def test_expired_invitation_cannot_be_used(self):
        self.client.force_authenticate(self.superadmin)
        create_response = self.client.post(
            reverse(
                "organization-invitations",
                args=[self.other_organization.pk],
            ),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )
        invitation = OrganizationInvitation.objects.get(pk=create_response.data["id"])
        invitation.expires_at = timezone.now() - timedelta(seconds=1)
        invitation.save(update_fields=["expires_at"])

        self.client.force_authenticate(self.member)
        join_response = self.client.post(
            reverse("membership-join"),
            {"code": create_response.data["code"], "location_id": self.other_location.pk},
            format="json",
        )

        self.assertEqual(join_response.status_code, 400)
        self.assertFalse(
            OrganizationMembership.objects.filter(
                user=self.member,
                organization=self.other_organization,
            ).exists()
        )

    def test_suspended_organization_blocks_member_access(self):
        user_model = get_user_model()
        suspended_admin = user_model.objects.create_user(
            username="suspended_org_admin",
            email="suspended_org_admin@example.test",
            password="Secure-Test-Password-123",
            role=user_model.Role.ADMIN,
        )
        OrganizationMembership.objects.create(
            organization=self.other_organization,
            user=suspended_admin,
            role=OrganizationMembership.Role.ADMIN,
        )
        self.client.force_authenticate(self.superadmin)
        status_response = self.client.patch(
            reverse("organization-status", args=[self.other_organization.pk]),
            {"status": Organization.Status.SUSPENDED},
            format="json",
        )

        self.client.force_authenticate(suspended_admin)
        blocked_response = self.client.get(
            reverse("location-list"),
            HTTP_X_ORGANIZATION_ID=str(self.other_organization.pk),
        )

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(blocked_response.status_code, 403)


class OrganizationBackfillMigrationTests(TransactionTestCase):
    migrate_from = [
        ("accounts", "0002_add_organizations_and_memberships"),
        ("incidents", "0002_add_organizations_and_memberships"),
    ]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps
        OldUser = old_apps.get_model("accounts", "User")
        OldLocation = old_apps.get_model("accounts", "Location")
        OldCategory = old_apps.get_model("incidents", "Category")
        OldIncident = old_apps.get_model("incidents", "Incident")

        real_location = OldLocation.objects.create(name="Real", code="REAL-1")
        demo_location = OldLocation.objects.create(name="Demo", code="DEMO-A")
        real_user = OldUser.objects.create_user(
            username="migration_real",
            email="migration_real@example.test",
            password="Secure-Test-Password-123",
            role="student",
            location=real_location,
        )
        demo_user = OldUser.objects.create_user(
            username="migration_demo",
            email="migration_demo@example.test",
            password="Secure-Test-Password-123",
            role="student",
            location=demo_location,
        )
        old_admin = OldUser.objects.create_user(
            username="migration_admin",
            email="migration_admin@example.test",
            password="Secure-Test-Password-123",
            role="admin",
        )
        old_superadmin = OldUser.objects.create(
            username="migration_superadmin",
            email="migration_superadmin@example.test",
            password="unusable",
            role="admin",
            is_superuser=True,
            is_staff=True,
            is_active=True,
        )
        category = OldCategory.objects.create(name="Compartida")
        OldIncident.objects.create(
            title="Incidencia real",
            description="Registro real",
            category=category,
            location=real_location,
            reported_by=real_user,
        )
        OldIncident.objects.create(
            title="Incidencia demo",
            description="Registro demo",
            category=category,
            location=demo_location,
            reported_by=demo_user,
        )
        self.usernames = {
            "real": real_user.username,
            "demo": demo_user.username,
            "admin": old_admin.username,
            "superadmin": old_superadmin.username,
        }

    def test_existing_records_are_backfilled_and_migration_reverses(self):
        executor = MigrationExecutor(connection)
        migrate_to = executor.loader.graph.leaf_nodes()
        executor.migrate(migrate_to)
        apps = executor.loader.project_state(migrate_to).apps
        Organization = apps.get_model("accounts", "Organization")
        OrganizationMembership = apps.get_model("accounts", "OrganizationMembership")
        User = apps.get_model("accounts", "User")
        Location = apps.get_model("accounts", "Location")
        Category = apps.get_model("incidents", "Category")
        Incident = apps.get_model("incidents", "Incident")

        real_org = Organization.objects.get(slug="universidad-de-la-guajira")
        demo_org = Organization.objects.get(slug="nefijj-demo")
        self.assertEqual(
            Location.objects.get(code="REAL-1").organization_id,
            real_org.pk,
        )
        self.assertEqual(
            Location.objects.get(code="DEMO-A").organization_id,
            demo_org.pk,
        )
        self.assertEqual(
            Incident.objects.get(title="Incidencia real").organization_id,
            real_org.pk,
        )
        self.assertEqual(
            Incident.objects.get(title="Incidencia demo").organization_id,
            demo_org.pk,
        )
        self.assertEqual(
            Category.objects.filter(name="Compartida").values("organization_id").distinct().count(),
            2,
        )
        for incident in Incident.objects.all():
            self.assertEqual(incident.category.organization_id, incident.organization_id)
        self.assertEqual(
            OrganizationMembership.objects.get(user__username=self.usernames["real"]).role,
            "user",
        )
        self.assertEqual(
            OrganizationMembership.objects.get(user__username=self.usernames["demo"]).organization_id,
            demo_org.pk,
        )
        self.assertEqual(
            OrganizationMembership.objects.get(user__username=self.usernames["real"]).location_id,
            Location.objects.get(code="REAL-1").pk,
        )
        self.assertEqual(
            OrganizationMembership.objects.get(user__username=self.usernames["admin"]).role,
            "organization_admin",
        )
        self.assertEqual(
            User.objects.get(username=self.usernames["superadmin"]).role,
            "superadmin",
        )

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        apps = executor.loader.project_state(self.migrate_from).apps
        OldUser = apps.get_model("accounts", "User")
        OldOrganization = apps.get_model("accounts", "Organization")
        OldCategory = apps.get_model("incidents", "Category")
        OldIncident = apps.get_model("incidents", "Incident")
        OldLocation = apps.get_model("accounts", "Location")
        self.assertEqual(OldOrganization.objects.count(), 0)
        self.assertEqual(OldCategory.objects.filter(name="Compartida").count(), 1)
        self.assertTrue(
            OldLocation.objects.filter(organization__isnull=True).exists()
        )
        self.assertTrue(
            OldIncident.objects.filter(organization__isnull=True).exists()
        )
        self.assertEqual(
            OldUser.objects.get(username=self.usernames["superadmin"]).role,
            "admin",
        )

        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
