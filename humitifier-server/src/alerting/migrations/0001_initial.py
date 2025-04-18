# Generated by Django 5.1.6 on 2025-03-11 12:09

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("hosts", "0022_delete_alert"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Alert",
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
                ("_creator", models.CharField(max_length=255)),
                (
                    "custom_identifier",
                    models.CharField(
                        blank=True,
                        help_text="Used during alert-checking to differentiate between instances of an alert",
                        max_length=255,
                        null=True,
                        verbose_name="Custom identifier",
                    ),
                ),
                (
                    "short_message",
                    models.CharField(max_length=255, verbose_name="Short message"),
                ),
                (
                    "message",
                    models.TextField(
                        blank=True, null=True, verbose_name="Full message"
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("info", "Info"),
                            ("warning", "Warning"),
                            ("critical", "Critical"),
                        ],
                        max_length=50,
                        verbose_name="Severity",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="First occurrence"
                    ),
                ),
                (
                    "last_seen_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Last occurrence"
                    ),
                ),
                ("_notified", models.BooleanField(default=False)),
                ("_can_acknowledge", models.BooleanField(default=True)),
                (
                    "host",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alerts",
                        to="hosts.host",
                    ),
                ),
                (
                    "scan",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="hosts.scan",
                    ),
                ),
            ],
            options={
                "unique_together": {("host", "_creator", "custom_identifier")},
            },
        ),
        migrations.CreateModel(
            name="AlertAcknowledgment",
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
                ("_creator", models.CharField(max_length=255)),
                (
                    "custom_identifier",
                    models.CharField(
                        blank=True,
                        help_text="Used during alert-checking to differentiate between instances of an alert",
                        max_length=255,
                        null=True,
                        verbose_name="Custom identifier",
                    ),
                ),
                ("acknowledged_at", models.DateTimeField(auto_now_add=True)),
                ("reason", models.TextField()),
                ("persistent", models.BooleanField(default=False)),
                (
                    "_alert",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="acknowledgement",
                        to="alerting.alert",
                    ),
                ),
                (
                    "acknowledged_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "host",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alert_acknowledgements",
                        to="hosts.host",
                    ),
                ),
            ],
            options={
                "unique_together": {("host", "_creator", "custom_identifier")},
            },
        ),
    ]
