# Generated by Django 5.1.3 on 2025-01-09 13:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hosts", "0014_host_customer_alter_host_contact_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="host",
            name="has_tofu_config",
            field=models.BooleanField(default=False),
        ),
    ]
