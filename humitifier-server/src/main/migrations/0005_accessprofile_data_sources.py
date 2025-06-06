# Generated by Django 5.1.3 on 2024-12-09 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hosts", "0010_datasource_host_data_source"),
        ("main", "0004_alter_user_default_home_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="accessprofile",
            name="data_sources",
            field=models.ManyToManyField(
                help_text="Determines which data sources this access profile gives manage access to.",
                to="hosts.datasource",
                verbose_name="Manage data sources",
            ),
        ),
    ]
