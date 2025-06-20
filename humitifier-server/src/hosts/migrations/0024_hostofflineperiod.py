# Generated by Django 5.1.9 on 2025-06-13 14:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hosts", "0023_host_billable"),
    ]

    operations = [
        migrations.CreateModel(
            name="HostOfflinePeriod",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("start_date", models.DateTimeField()),
                ("end_date", models.DateTimeField(blank=True, null=True)),
                (
                    "host",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offline_periods",
                        to="hosts.host",
                    ),
                ),
            ],
        ),
    ]
