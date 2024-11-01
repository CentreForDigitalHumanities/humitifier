# Generated by Django 5.1.2 on 2024-10-31 15:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hosts", "0007_alter_alert_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="host",
            name="archival_date",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="host",
            name="archived",
            field=models.BooleanField(default=False),
        ),
    ]