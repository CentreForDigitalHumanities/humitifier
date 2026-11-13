import json
from django.db import migrations, models


def convert_columns_to_json(apps, schema_editor):
    SavedSearch = apps.get_model("hosts", "SavedSearch")
    for search in SavedSearch.objects.all():
        cols = search.columns
        if not cols:
            search.columns = "[]"
        elif isinstance(cols, list):
            search.columns = json.dumps([str(c).strip() for c in cols if str(c).strip()])
        elif isinstance(cols, str):
            try:
                parsed = json.loads(cols)
                if isinstance(parsed, list):
                    search.columns = json.dumps([str(c).strip() for c in parsed if str(c).strip()])
                else:
                    search.columns = json.dumps([c.strip() for c in cols.split(",") if c.strip()])
            except (json.JSONDecodeError, TypeError):
                search.columns = json.dumps([c.strip() for c in cols.split(",") if c.strip()])
        search.save(update_fields=["columns"])


def convert_json_to_columns(apps, schema_editor):
    SavedSearch = apps.get_model("hosts", "SavedSearch")
    for search in SavedSearch.objects.all():
        cols = search.columns
        if isinstance(cols, list):
            search.columns = ", ".join(cols)
        elif isinstance(cols, str):
            try:
                parsed = json.loads(cols)
                if isinstance(parsed, list):
                    search.columns = ", ".join(parsed)
            except Exception:
                pass
        search.save(update_fields=["columns"])


class Migration(migrations.Migration):

    dependencies = [
        ("hosts", "0029_seed_operating_systems"),
    ]

    operations = [
        migrations.AddField(
            model_name="savedsearch",
            name="show_matches",
            field=models.BooleanField(
                default=False,
                help_text="Automatically derive and show matched array element columns",
            ),
        ),
        migrations.RunPython(
            convert_columns_to_json,
            reverse_code=convert_json_to_columns,
        ),
        migrations.AlterField(
            model_name="savedsearch",
            name="columns",
            field=models.JSONField(
                default=list,
                help_text="List of column expressions",
            ),
        ),
    ]
