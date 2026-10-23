"""Tests for search column expressions, parsing, and SQL evaluation."""

import csv
import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from humitifier_common.artefacts import registry as artefact_registry

from hosts.forms import SavedSearchForm
from hosts.models import Host, SavedSearch
from hosts.search import (
    ColumnSpec,
    derive_match_columns,
    evaluate_columns,
    format_value,
    parse_column,
    parse_query,
)
from hosts.search.constants import SearchFormParam
from hosts.tests.test_advanced_search import AdvancedSearchTestCase

User = get_user_model()


class ColumnParserTests(TestCase):
    """Test parsing column expressions with optional aliases and validation."""

    def test_parse_plain_field(self):
        spec = parse_column("facts.generic.HostnameCtl.os")
        self.assertIsInstance(spec, ColumnSpec)
        self.assertEqual(spec.source, "facts.generic.HostnameCtl.os")
        self.assertEqual(spec.label, "facts.generic.HostnameCtl.os")
        self.assertIsNone(spec.alias)

    def test_parse_field_with_alias(self):
        spec = parse_column('facts.generic.HostnameCtl.os AS "Operating System"')
        self.assertIsInstance(spec, ColumnSpec)
        self.assertEqual(spec.alias, "Operating System")
        self.assertEqual(spec.label, "Operating System")

    def test_parse_meta_field(self):
        spec = parse_column('meta.fqdn AS "Host FQDN"')
        self.assertEqual(spec.alias, "Host FQDN")
        self.assertEqual(spec.label, "Host FQDN")

    def test_parse_filter_expression(self):
        spec = parse_column(
            'filter(facts.generic.PackageManagerInfo.installed_packages[].name, "^apache") AS "Apache PKGs"'
        )
        self.assertEqual(spec.alias, "Apache PKGs")
        self.assertEqual(spec.label, "Apache PKGs")

    def test_parse_count_expression(self):
        spec = parse_column("count(facts.generic.Users[].name)")
        self.assertIsNone(spec.alias)
        self.assertEqual(spec.label, "count(facts.generic.Users[].name)")

    def test_reject_match_predicate(self):
        with self.assertRaises(ValueError) as ctx:
            parse_column(
                "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'apache')"
            )
        self.assertIn(
            "Boolean predicate function 'match' cannot be used as a column",
            str(ctx.exception),
        )

    def test_reject_unknown_field(self):
        with self.assertRaises(ValueError) as ctx:
            parse_column("unknown.nonexistent.field")
        self.assertIn("Unknown field", str(ctx.exception))

    def test_reject_unknown_function(self):
        with self.assertRaises(ValueError) as ctx:
            parse_column("nonexistent_func(meta.fqdn)")
        self.assertIn("Unknown function", str(ctx.exception))

    def test_reject_empty(self):
        with self.assertRaises(ValueError):
            parse_column("")
        with self.assertRaises(ValueError):
            parse_column("   ")

    def test_reject_missing_alias_string(self):
        with self.assertRaises(ValueError) as ctx:
            parse_column("meta.fqdn AS")
        self.assertIn("Expected string literal alias after AS", str(ctx.exception))


class ColumnFormattingTests(TestCase):
    """Test format_value for various types."""

    def test_format_none(self):
        self.assertEqual(format_value(None), "")

    def test_format_scalar(self):
        self.assertEqual(format_value("Ubuntu"), "Ubuntu")
        self.assertEqual(format_value(42), "42")
        self.assertEqual(format_value(True), "True")
        self.assertEqual(format_value(False), "False")

    def test_format_list(self):
        self.assertEqual(format_value(["apache2", "nginx"]), "apache2, nginx")
        self.assertEqual(format_value([]), "")

    def test_format_dict(self):
        val = {"name": "php-cli", "version": "7.4"}
        self.assertEqual(format_value(val), "name: php-cli; version: 7.4")

    def test_format_list_of_dicts(self):
        val = [
            {"name": "php-cli", "version": "7.4"},
            {"name": "php-fpm", "version": "7.4"},
        ]
        self.assertEqual(
            format_value(val),
            "name: php-cli; version: 7.4, name: php-fpm; version: 7.4",
        )


class ColumnEvaluationTests(AdvancedSearchTestCase):
    """Test SQL evaluation of columns using evaluate_columns."""

    def test_evaluate_meta_field(self):
        spec = parse_column('meta.fqdn AS "FQDN"')
        results = evaluate_columns(
            Host.objects.filter(fqdn="web01.example.com"), [spec]
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["fields"]["FQDN"], "web01.example.com")

    def test_evaluate_scalar_fact(self):
        spec = parse_column('facts.generic.HostnameCtl.os AS "OS"')
        results = evaluate_columns(
            Host.objects.filter(fqdn="web01.example.com"), [spec]
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["fields"]["OS"], "Ubuntu 22.04.3 LTS")

    def test_evaluate_array_field(self):
        spec = parse_column("facts.generic.Users[].name")
        results = evaluate_columns(
            Host.objects.filter(fqdn="web01.example.com"), [spec]
        )
        self.assertEqual(len(results), 1)
        names = results[0]["fields"]["facts.generic.Users[].name"]
        self.assertIn("root", names)
        self.assertIn("www-data", names)

    def test_evaluate_filter_function(self):
        spec = parse_column(
            'filter(facts.generic.PackageManagerInfo.installed_packages[].name, "^apache") AS "Apache"'
        )
        results = evaluate_columns(
            Host.objects.filter(fqdn="web01.example.com"), [spec]
        )
        self.assertEqual(len(results), 1)
        pkgs = results[0]["fields"]["Apache"]
        self.assertEqual(pkgs, ["apache2"])

    def test_evaluate_count_function(self):
        spec = parse_column('count(facts.generic.Users[].name) AS "User Count"')
        results = evaluate_columns(
            Host.objects.filter(fqdn="web01.example.com"), [spec]
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["fields"]["User Count"], 2)

    def test_evaluate_outdated_or_missing_cache(self):
        # Host without cache
        no_cache_host = Host.objects.create(fqdn="nocache.example.com")
        # Host with outdated version
        old_host = Host.objects.create(
            fqdn="old.example.com",
            last_scan_cache={
                "version": artefact_registry.latest_version - 1,
                "facts": {},
            },
        )

        spec_scalar = parse_column("facts.generic.HostnameCtl.os")
        spec_array = parse_column("facts.generic.Users[].name")
        spec_meta = parse_column("meta.fqdn")

        results = evaluate_columns(
            Host.objects.filter(
                fqdn__in=["nocache.example.com", "old.example.com"]
            ).order_by("fqdn"),
            [spec_meta, spec_scalar, spec_array],
        )
        self.assertEqual(len(results), 2)
        # Meta works even without cache
        self.assertEqual(results[0]["fields"]["meta.fqdn"], "nocache.example.com")
        self.assertIsNone(results[0]["fields"]["facts.generic.HostnameCtl.os"])
        self.assertIsNone(results[0]["fields"]["facts.generic.Users[].name"])

        self.assertEqual(results[1]["fields"]["meta.fqdn"], "old.example.com")
        self.assertIsNone(results[1]["fields"]["facts.generic.HostnameCtl.os"])
        self.assertIsNone(results[1]["fields"]["facts.generic.Users[].name"])


class DerivedMatchColumnsTests(AdvancedSearchTestCase):
    """Test derive_match_columns and evaluating derived match columns."""

    def test_derive_from_match_function(self):
        query = parse_query(
            "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
            "facts.generic.PackageManagerInfo.installed_packages[].current_version, '8.1')"
        )
        derived = derive_match_columns(query)
        self.assertEqual(len(derived), 1)
        self.assertTrue(derived[0].derived)
        self.assertEqual(
            derived[0].label,
            'Matches: match(facts.generic.PackageManagerInfo.installed_packages[].name, "php", facts.generic.PackageManagerInfo.installed_packages[].current_version, "8.1")',
        )

        results = evaluate_columns(
            Host.objects.filter(fqdn="web01.example.com"), derived
        )
        self.assertEqual(len(results), 1)
        matches = results[0]["fields"][derived[0].label]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["name"], "php8.1")
        self.assertEqual(matches[0]["current_version"], "8.1.2-1ubuntu2.14")

    def test_derive_from_array_comparison(self):
        query = parse_query(
            'facts.generic.PackageManagerInfo.installed_packages[].name contains "ssh"'
        )
        derived = derive_match_columns(query)
        self.assertEqual(len(derived), 1)
        self.assertTrue(derived[0].derived)
        self.assertEqual(
            derived[0].label,
            'Matches: facts.generic.PackageManagerInfo.installed_packages[].name CONTAINS "ssh"',
        )

        results = evaluate_columns(
            Host.objects.filter(fqdn="web01.example.com"), derived
        )
        self.assertEqual(len(results), 1)
        matches = results[0]["fields"][derived[0].label]
        self.assertEqual(matches, ["openssh-server"])

    def test_skip_not_and_scalar_and_meta(self):
        query = parse_query(
            'meta.fqdn contains "web" and facts.generic.HostnameCtl.os contains "Ubuntu" '
            'and not {facts.generic.PackageManagerInfo.installed_packages[].name contains "mysql"}'
        )
        derived = derive_match_columns(query)
        self.assertEqual(len(derived), 0)

    def test_deduplication(self):
        query = parse_query(
            'facts.generic.PackageManagerInfo.installed_packages[].name contains "ssh" or '
            'facts.generic.PackageManagerInfo.installed_packages[].name contains "ssh"'
        )
        derived = derive_match_columns(query)
        self.assertEqual(len(derived), 1)

    def test_none_or_empty_query(self):
        self.assertEqual(derive_match_columns(None), [])
        query = parse_query('meta.fqdn = "web01.example.com"')
        self.assertEqual(derive_match_columns(query), [])


class SavedSearchModelAndFormTests(TestCase):
    """Test SavedSearch model column methods and SavedSearchForm validation."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")

    def test_saved_search_get_columns_list_native_list(self):
        s = SavedSearch(columns=["meta.fqdn", "facts.generic.HostnameCtl.os"])
        self.assertEqual(
            s.get_columns_list(), ["meta.fqdn", "facts.generic.HostnameCtl.os"]
        )

    def test_saved_search_set_columns_list(self):
        s = SavedSearch()
        s.set_columns_list(["meta.fqdn", 'filter(pkgs[].name, "php") AS "PHP"'])
        self.assertEqual(
            s.columns,
            ["meta.fqdn", 'filter(pkgs[].name, "php") AS "PHP"'],
        )
        self.assertEqual(
            s.get_columns_list(),
            ["meta.fqdn", 'filter(pkgs[].name, "php") AS "PHP"'],
        )

    def test_saved_search_form_valid_columns_and_show_matches(self):
        form = SavedSearchForm(
            data={
                "title": "Test",
                "query": 'meta.fqdn = "web01"',
                "columns": json.dumps(['meta.fqdn AS "FQDN"']),
                "show_matches": True,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["columns"], ['meta.fqdn AS "FQDN"'])
        self.assertTrue(form.cleaned_data["show_matches"])

    def test_saved_search_form_legacy_comma_normalised(self):
        form = SavedSearchForm(
            data={
                "title": "Test",
                "query": 'meta.fqdn = "web01"',
                "columns": "meta.fqdn, facts.generic.HostnameCtl.os",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["columns"],
            ["meta.fqdn", "facts.generic.HostnameCtl.os"],
        )

    def test_saved_search_form_invalid_column(self):
        form = SavedSearchForm(
            data={
                "title": "Test",
                "query": 'meta.fqdn = "web01"',
                "columns": "invalid_func(foo)",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("columns", form.errors)

    def test_migration_convert_columns(self):
        import importlib

        migration_mod = importlib.import_module(
            "hosts.migrations.0030_savedsearch_show_matches"
        )
        convert_columns_to_json = migration_mod.convert_columns_to_json
        convert_json_to_columns = migration_mod.convert_json_to_columns

        class DummyModel:
            def __init__(self, cols):
                self.columns = cols

            def save(self, update_fields=None):
                pass

        class DummyApps:
            def __init__(self, records):
                self.records = records

            def get_model(self, app_label, model_name):
                records = self.records

                class DummyManager:
                    @staticmethod
                    def all():
                        return records

                class Model:
                    objects = DummyManager

                return Model

        r1 = DummyModel("meta.fqdn, facts.generic.os")
        r2 = DummyModel('["meta.fqdn"]')
        r3 = DummyModel("")
        apps = DummyApps([r1, r2, r3])

        convert_columns_to_json(apps, None)
        self.assertEqual(json.loads(r1.columns), ["meta.fqdn", "facts.generic.os"])
        self.assertEqual(json.loads(r2.columns), ["meta.fqdn"])
        self.assertEqual(r3.columns, "[]")

        convert_json_to_columns(apps, None)
        self.assertEqual(r1.columns, "meta.fqdn, facts.generic.os")
        self.assertEqual(r2.columns, "meta.fqdn")


class AdvancedSearchViewIntegrationTests(AdvancedSearchTestCase):
    """Test AdvancedSearchView with JSON columns, show matches, exports, and errors."""

    def setUp(self):
        super().setUp()
        self.superuser = User.objects.create_superuser(
            username="admin", password="password", email="admin@example.com"
        )
        self.client.login(username="admin", password="password")

    def test_post_json_columns_and_show_matches(self):
        response = self.client.post(
            reverse("hosts:advanced_search"),
            {
                SearchFormParam.COLUMNS: json.dumps(['meta.fqdn AS "Host FQDN"']),
                SearchFormParam.SHOW_MATCHES: "1",
                SearchFormParam.SEARCH_STRING: 'facts.generic.PackageManagerInfo.installed_packages[].name contains "ssh"',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["show_matches"])
        columns = response.context["columns"]
        self.assertEqual(len(columns), 2)
        labels = [c.label for c in columns]
        self.assertIn("Host FQDN", labels)
        self.assertTrue(any(l.startswith("Matches: ") for l in labels))
        data = response.context["data"]
        self.assertEqual(len(data), 3)  # web01, db01, storage01 (unarchived) have ssh

    def test_post_legacy_comma_columns(self):
        response = self.client.post(
            reverse("hosts:advanced_search"),
            {SearchFormParam.COLUMNS: "meta.fqdn, facts.generic.HostnameCtl.os"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["columns"]), 2)

    def test_invalid_column_shows_error_and_renders_valid_columns(self):
        response = self.client.post(
            reverse("hosts:advanced_search"),
            {SearchFormParam.COLUMNS: json.dumps(["meta.fqdn", "bad.field.expr"])},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["column_errors"]), 1)
        self.assertEqual(
            response.context["column_errors"][0]["column"], "bad.field.expr"
        )
        self.assertEqual(len(response.context["columns"]), 1)
        self.assertEqual(response.context["columns"][0].source, "meta.fqdn")
        data = response.context["data"]
        self.assertTrue(len(data) > 0)
        self.assertIn("meta.fqdn", data[0]["fields"])

    def test_export_csv(self):
        response = self.client.post(
            reverse("hosts:advanced_search"),
            {
                "export-csv": "1",
                SearchFormParam.COLUMNS: json.dumps(
                    [
                        'meta.fqdn AS "FQDN Label"',
                        'facts.generic.Users[].name AS "Users"',
                    ]
                ),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        content = response.content.decode("utf-8")
        reader = csv.reader(StringIO(content))
        header = next(reader)
        self.assertEqual(header, ["FQDN", "FQDN Label", "Users"])
        first_row = next(reader)
        self.assertTrue(len(first_row) == 3)
        self.assertIn("root", first_row[2])

    def test_export_json(self):
        response = self.client.post(
            reverse("hosts:advanced_search"),
            {
                "export-json": "1",
                SearchFormParam.COLUMNS: json.dumps(['meta.fqdn AS "FQDN Label"']),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        parsed = json.loads(response.content.decode("utf-8"))
        self.assertTrue(isinstance(parsed, list))
        self.assertIn("FQDN", parsed[0])
        self.assertIn("FQDN Label", parsed[0])

    def test_load_saved_search(self):
        saved = SavedSearch.objects.create(
            creator=self.superuser,
            title="Saved",
            query='meta.fqdn contains "web"',
            columns=['meta.fqdn AS "FQDN"'],
            show_matches=True,
        )
        response = self.client.get(
            reverse("hosts:advanced_search") + f"?load={saved.pk}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["show_matches"])
        self.assertEqual(response.context["search_string"], 'meta.fqdn contains "web"')
        self.assertEqual(len(response.context["columns"]), 1)
        self.assertEqual(response.context["columns"][0].label, "FQDN")
