# Data migration to seed the OperatingSystem model

from django.db import migrations

# The list of outdated OSes that used to be hardcoded in
# alerting.alerts.generic.OutdatedOSAlertGenerator
OUTDATED_OSES = [
    "Debian GNU/Linux 11 (bullseye)",
    "Debian GNU/Linux 10 (buster)",
    "Debian GNU/Linux 9 (stretch)",
    "CentOS Linux 7 (Core)",
]


def seed_operating_systems(apps, schema_editor):
    OperatingSystem = apps.get_model("hosts", "OperatingSystem")
    Host = apps.get_model("hosts", "Host")

    # Seed the (previously hardcoded) outdated OSes
    for os_name in OUTDATED_OSES:
        OperatingSystem.objects.update_or_create(
            name=os_name,
            defaults={"outdated": True},
        )

    # Also seed all OSes currently known from hosts, so the list is complete
    known_oses = (
        Host.objects.exclude(os=None)
        .exclude(os="")
        .values_list("os", flat=True)
        .order_by()
        .distinct()
    )

    # Strip with leading/trailing quotes
    known_oses = set([os_name.strip('"') for os_name in known_oses])

    for os_name in known_oses:
        OperatingSystem.objects.get_or_create(name=os_name)


def remove_operating_systems(apps, schema_editor):
    OperatingSystem = apps.get_model("hosts", "OperatingSystem")
    OperatingSystem.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("hosts", "0028_operatingsystem"),
    ]

    operations = [
        migrations.RunPython(seed_operating_systems, remove_operating_systems),
    ]
