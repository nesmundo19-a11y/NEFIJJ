from django.db import migrations


MYSQL_TABLE_DEFINITIONS = {
    "IncidentEvent": """
        CREATE TABLE `incidents_incidentevent` (
            `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            `event_type` VARCHAR(30) NOT NULL,
            `old_value` JSON NULL,
            `new_value` JSON NULL,
            `created_at` DATETIME(6) NOT NULL,
            `actor_id` INT NOT NULL,
            `incident_id` INT NOT NULL,
            CONSTRAINT `incident_event_actor_fk`
                FOREIGN KEY (`actor_id`) REFERENCES `accounts_user` (`id`)
                ON DELETE RESTRICT,
            CONSTRAINT `incident_event_incident_fk`
                FOREIGN KEY (`incident_id`) REFERENCES `incidents_incident` (`id`)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "EmergencyProtocol": """
        CREATE TABLE `incidents_emergencyprotocol` (
            `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            `title` VARCHAR(150) NOT NULL,
            `content` LONGTEXT NOT NULL,
            `contact_phone` VARCHAR(30) NOT NULL,
            `is_active` TINYINT(1) NOT NULL DEFAULT 1,
            `created_at` DATETIME(6) NOT NULL,
            `updated_at` DATETIME(6) NOT NULL,
            `location_id` INT NOT NULL,
            CONSTRAINT `emergency_protocol_location_fk`
                FOREIGN KEY (`location_id`) REFERENCES `accounts_location` (`id`)
                ON DELETE RESTRICT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
}


def create_missing_legacy_tables(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    for model_name in ("IncidentEvent", "EmergencyProtocol"):
        model = apps.get_model("incidents", model_name)
        table_name = model._meta.db_table
        if table_name not in existing_tables:
            if connection.vendor == "mysql":
                schema_editor.execute(MYSQL_TABLE_DEFINITIONS[model_name])
            else:
                schema_editor.create_model(model)
            existing_tables.add(table_name)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("accounts", "0005_backfill_membership_location"),
        ("incidents", "0003_backfill_organization_scope"),
    ]

    operations = [
        migrations.RunPython(
            create_missing_legacy_tables,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
