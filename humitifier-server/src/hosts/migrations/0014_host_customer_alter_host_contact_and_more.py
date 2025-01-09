# Handcrafted for your enjoyment

from django.db import migrations, models


def set_new_values(apps, schema_editor):
    Host = apps.get_model("hosts", "Host")

    for host in Host.objects.all():
        host_meta = host.last_scan_cache.get("HostMeta", None)
        if host_meta:
            # customer is the new department, as department now has different semantics
            host.customer = host_meta.get("department", None)
            host.contact = host_meta.get("contact", None)
            host.save()


class Migration(migrations.Migration):

    dependencies = [
        ("hosts", "0013_auto_20250108_1415"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="host",
            name="department",
        ),
        migrations.RemoveField(
            model_name="host",
            name="contact",
        ),
        migrations.AddField(
            model_name="host",
            name="customer",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="host",
            name="contact",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="host",
            name="department",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.RunPython(set_new_values, migrations.RunPython.noop),
    ]
