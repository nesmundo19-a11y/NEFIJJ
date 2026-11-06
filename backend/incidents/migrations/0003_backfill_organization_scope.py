import django.db.models.deletion
from django.db import migrations, models


REAL_ORGANIZATION = "universidad-de-la-guajira"
DEMO_ORGANIZATION = "nefijj-demo"


def assign_existing_data(apps, schema_editor):
    database = schema_editor.connection.alias
    Organization = apps.get_model("accounts", "Organization")
    OrganizationMembership = apps.get_model("accounts", "OrganizationMembership")
    User = apps.get_model("accounts", "User")
    Location = apps.get_model("accounts", "Location")
    Category = apps.get_model("incidents", "Category")
    Incident = apps.get_model("incidents", "Incident")

    real_org, _ = Organization.objects.using(database).get_or_create(
        slug=REAL_ORGANIZATION,
        defaults={"name": "Universidad de La Guajira", "status": "active"},
    )
    demo_org, _ = Organization.objects.using(database).get_or_create(
        slug=DEMO_ORGANIZATION,
        defaults={"name": "NEFIJJ - Datos DEMO", "status": "active"},
    )

    for location in Location.objects.using(database).all().iterator():
        organization = demo_org if location.code.upper().startswith("DEMO-") else real_org
        Location.objects.using(database).filter(pk=location.pk).update(
            organization_id=organization.pk,
        )

    for incident in Incident.objects.using(database).select_related("location").iterator():
        Incident.objects.using(database).filter(pk=incident.pk).update(
            organization_id=incident.location.organization_id,
        )

    for category in Category.objects.using(database).all().iterator():
        organization_ids = list(
            Incident.objects.using(database)
            .filter(category_id=category.pk)
            .order_by()
            .values_list("organization_id", flat=True)
            .distinct()
        )
        if not organization_ids:
            category.organization_id = real_org.pk
            category.save(using=database, update_fields=["organization"])
            continue

        category.organization_id = organization_ids[0]
        category.save(using=database, update_fields=["organization"])
        for organization_id in organization_ids[1:]:
            scoped_category, _ = Category.objects.using(database).get_or_create(
                organization_id=organization_id,
                name=category.name,
                defaults={
                    "description": category.description,
                    "is_active": category.is_active,
                },
            )
            Incident.objects.using(database).filter(
                category_id=category.pk,
                organization_id=organization_id,
            ).update(category_id=scoped_category.pk)

    for user in User.objects.using(database).all().iterator():
        if user.is_superuser:
            continue

        if user.role == "admin":
            organization_id = real_org.pk
            membership_role = "organization_admin"
        else:
            if user.location_id is None:
                raise RuntimeError(
                    f"Cannot migrate user {user.pk}: non-admin user has no location."
                )
            organization_id = Location.objects.using(database).values_list(
                "organization_id",
                flat=True,
            ).get(pk=user.location_id)
            membership_role = {
                "technician": "technician",
                "student": "user",
            }.get(user.role, "user")

        OrganizationMembership.objects.using(database).get_or_create(
            organization_id=organization_id,
            user_id=user.pk,
            defaults={"role": membership_role, "is_active": user.is_active},
        )


def unassign_existing_data(apps, schema_editor):
    database = schema_editor.connection.alias
    Organization = apps.get_model("accounts", "Organization")
    OrganizationMembership = apps.get_model("accounts", "OrganizationMembership")
    User = apps.get_model("accounts", "User")
    Location = apps.get_model("accounts", "Location")
    Category = apps.get_model("incidents", "Category")
    Incident = apps.get_model("incidents", "Incident")

    OrganizationMembership.objects.using(database).all().delete()
    Incident.objects.using(database).update(organization_id=None)

    categories = {}
    for category in Category.objects.using(database).order_by("pk").iterator():
        original = categories.setdefault(category.name, category.pk)
        if category.pk != original:
            Incident.objects.using(database).filter(category_id=category.pk).update(
                category_id=original,
            )
            Category.objects.using(database).filter(pk=category.pk).delete()
    Category.objects.using(database).update(organization_id=None)
    Location.objects.using(database).update(organization_id=None)
    Organization.objects.using(database).filter(
        slug__in=[REAL_ORGANIZATION, DEMO_ORGANIZATION],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_add_organizations_and_memberships"),
        ("incidents", "0002_add_organizations_and_memberships"),
    ]

    operations = [
        migrations.RunPython(assign_existing_data, unassign_existing_data),
        migrations.AlterField(
            model_name="category",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="categories",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="incident",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="incidents",
                to="accounts.organization",
            ),
        ),
        migrations.AddIndex(
            model_name="incident",
            index=models.Index(
                fields=["organization", "status"],
                name="incidents_i_organiz_09b358_idx",
            ),
        ),
    ]
