from django.db import migrations, models


def set_membership_locations(apps, schema_editor):
    database = schema_editor.connection.alias
    OrganizationMembership = apps.get_model("accounts", "OrganizationMembership")
    for membership in OrganizationMembership.objects.using(database).select_related(
        "user",
        "user__location",
    ).iterator():
        location = membership.user.location
        if location is not None and location.organization_id == membership.organization_id:
            membership.location_id = location.pk
            membership.save(using=database, update_fields=["location"])
        elif membership.role != "organization_admin":
            raise RuntimeError(
                f"Cannot migrate membership {membership.pk}: a same-organization location is required."
            )


def clear_membership_locations(apps, schema_editor):
    database = schema_editor.connection.alias
    OrganizationMembership = apps.get_model("accounts", "OrganizationMembership")
    OrganizationMembership.objects.using(database).update(location_id=None)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_add_membership_location"),
        ("incidents", "0003_backfill_organization_scope"),
    ]

    operations = [
        migrations.RunPython(set_membership_locations, clear_membership_locations),
        migrations.AddConstraint(
            model_name="organizationmembership",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("role", "organization_admin"),
                    ("location__isnull", False),
                    _connector="OR",
                ),
                name="organization_member_requires_location",
            ),
        ),
    ]
