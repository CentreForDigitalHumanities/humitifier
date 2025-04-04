# Generated by Django 5.1.6 on 2025-02-20 15:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scanning", "0003_rename_scan_profile_artefactspec_scan_spec"),
    ]

    operations = [
        migrations.AlterField(
            model_name="artefactspec",
            name="knockout",
            field=models.BooleanField(
                default=False,
                help_text="If enabled, the specified artefact will NOT be included. This can be used to disable a specific artefact included through a group.",
            ),
        ),
    ]
