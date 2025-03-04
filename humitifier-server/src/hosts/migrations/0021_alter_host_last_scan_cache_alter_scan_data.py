# Generated by Django 5.1.6 on 2025-03-04 14:57

import hosts.json
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hosts", "0020_host_last_scan_scheduled"),
    ]

    operations = [
        migrations.AlterField(
            model_name="host",
            name="last_scan_cache",
            field=models.JSONField(
                decoder=hosts.json.HostJSONDecoder,
                encoder=hosts.json.HostJSONEncoder,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="scan",
            name="data",
            field=models.JSONField(
                decoder=hosts.json.HostJSONDecoder, encoder=hosts.json.HostJSONEncoder
            ),
        ),
    ]
