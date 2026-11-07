import django.db.models.deletion
from django.db import migrations, models


def promote_superusers(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.using(schema_editor.connection.alias).filter(
        is_superuser=True,
    ).exclude(role="superadmin").update(role="superadmin")


def demote_superusers(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.using(schema_editor.connection.alias).filter(
        role="superadmin",
        is_superuser=True,
    ).update(role="admin")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_add_organizations_and_memberships"),
        ("incidents", "0003_backfill_organization_scope"),
    ]

    operations = [
        migrations.AlterField(
            model_name="location",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="locations",
                to="accounts.organization",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="user",
            name="user_non_admin_requires_location",
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("role__in", ["admin", "superadmin"]),
                    ("location__isnull", False),
                    _connector="OR",
                ),
                name="user_non_admin_requires_location",
            ),
        ),
        migrations.RunPython(promote_superusers, demote_superusers),
    ]
