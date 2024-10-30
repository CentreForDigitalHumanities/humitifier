# Generated by Django 5.1.2 on 2024-10-24 17:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hosts", "0005_alert"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="host",
            options={"ordering": ["fqdn"]},
        ),
        migrations.AddField(
            model_name="host",
            name="os",
            field=models.GeneratedField(
                db_persist=True,
                expression=models.Case(
                    models.When(
                        last_scan_cache__HostnameCtl__os="null", then=models.Value(None)
                    ),
                    models.When(
                        last_scan_cache__HostnameCtl__os=None, then=models.Value(None)
                    ),
                    default=models.F("last_scan_cache__HostnameCtl__os"),
                ),
                output_field=models.CharField(max_length=255),
            ),
        ),
    ]