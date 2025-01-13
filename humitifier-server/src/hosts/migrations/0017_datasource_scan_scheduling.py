# Generated by Django 5.1.4 on 2025-01-13 10:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hosts", "0016_host_otap_stage"),
    ]

    operations = [
        migrations.AddField(
            model_name="datasource",
            name="scan_scheduling",
            field=models.CharField(
                choices=[
                    ("manual", "Manual/host initiated scanning"),
                    ("scheduled", "Scheduled scanning"),
                ],
                default="scheduled",
                max_length=255,
            ),
        ),
    ]
