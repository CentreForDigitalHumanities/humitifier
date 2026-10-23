"""Comprehensive tests for the built-in MatchElements ('match') search function."""

from unittest import mock

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from humitifier_common.artefacts import registry as artefact_registry

from hosts.models import Host, Scan
from hosts.search import (
    get_language_spec,
    parse_query,
    search_hosts_by_scan_fields,
)
from hosts.search.constants import Cardinality, ValueType
from hosts.search.functions.matching import MatchElements


class SearchMatchingValidationTestCase(TestCase):
    """Unit tests for MatchElements parse-time validation and error messages."""

    def test_validation_minimum_arity_empty(self):
        """Calling match() with no arguments raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            parse_query("match()")
        self.assertIn("requires at least 2 arguments", str(ctx.exception))

    def test_validation_minimum_arity_single_arg(self):
        """Calling match() with a single argument raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            parse_query("match(facts.generic.PackageManagerInfo.installed_packages[].name)")
        self.assertIn("requires at least 2 arguments", str(ctx.exception))

    def test_validation_odd_argument_count(self):
        """Calling match() with an odd number of arguments raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            parse_query(
                "match("
                "facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
                "facts.generic.PackageManagerInfo.installed_packages[].current_version"
                ")"
            )
        self.assertTrue(
            "repeated groups of 2" in str(ctx.exception)
            or "even number of arguments" in str(ctx.exception)
        )

    def test_validation_mismatched_arrays(self):
        """Pairing fields from different arrays raises ValueError with position."""
        with self.assertRaises(ValueError) as ctx:
            parse_query(
                "match("
                "facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
                "facts.generic.Users[].name, 'admin'"
                ")"
            )
        self.assertIn("All fields in 'match' must belong to the same array", str(ctx.exception))
        self.assertIn("position", str(ctx.exception))

    def test_validation_non_array_field(self):
        """Passing a scalar field to match() raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            parse_query("match(meta.fqdn, 'web01')")
        self.assertIn("requires an array field", str(ctx.exception))

    def test_validation_non_string_array_field(self):
        """Passing a non-string array field to match() raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            parse_query(
                "match("
                "facts.generic.PackageManagerInfo.installed_packages[].upgrade_available, 'true'"
                ")"
            )
        self.assertIn("requires an string array field", str(ctx.exception))

    def test_validation_non_literal_pattern(self):
        """Passing a field instead of a literal pattern raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            parse_query(
                "match("
                "facts.generic.PackageManagerInfo.installed_packages[].name, "
                "facts.generic.PackageManagerInfo.installed_packages[].current_version"
                ")"
            )
        self.assertIn("must be a literal", str(ctx.exception))

    def test_validation_non_string_literal_pattern(self):
        """Passing a non-string literal pattern raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            parse_query(
                "match(facts.generic.PackageManagerInfo.installed_packages[].name, 123)"
            )
        self.assertIn("requires an string field", str(ctx.exception))


class SearchMatchingExecutionTestCase(TestCase):
    """End-to-end integration tests for match() evaluation and query generation."""

    def setUp(self):
        self.now = timezone.now()

        # Host A (matching): Single package has BOTH name containing 'php' and version containing '7.0'
        self.host_matching = Host.objects.create(
            fqdn="matching.example.com",
            department="Engineering",
            customer="internal",
            archived=False,
            billable=True,
        )
        self._create_scan(
            self.host_matching,
            {
                "version": artefact_registry.latest_version,
                "scan_date": self.now.isoformat(),
                "hostname": "matching.example.com",
                "facts": {
                    "generic.HostnameCtl": {
                        "hostname": "matching",
                        "os": "Ubuntu 20.04",
                    },
                    "generic.PackageManagerInfo": {
                        "installed_packages": [
                            {
                                "name": "php7.0-cli",
                                "current_version": "7.0.33-0ubuntu0.16.04.16",
                                "arch": "amd64",
                                "upgrade_available": False,
                            },
                            {
                                "name": "apache2",
                                "current_version": "2.4.52",
                                "arch": "amd64",
                                "upgrade_available": False,
                            },
                        ]
                    },
                },
            },
        )

        # Host B (split-attribute anti-false-positive):
        # Has 'php8.1' (version 8.1.2) and 'python3' (version 7.0-custom).
        # Neither package has BOTH 'php' and '7.0'.
        self.host_split = Host.objects.create(
            fqdn="split.example.com",
            department="Engineering",
            customer="internal",
            archived=False,
            billable=True,
        )
        self._create_scan(
            self.host_split,
            {
                "version": artefact_registry.latest_version,
                "scan_date": self.now.isoformat(),
                "hostname": "split.example.com",
                "facts": {
                    "generic.HostnameCtl": {
                        "hostname": "split",
                        "os": "Debian 11",
                    },
                    "generic.PackageManagerInfo": {
                        "installed_packages": [
                            {
                                "name": "php8.1",
                                "current_version": "8.1.2-1ubuntu2",
                                "arch": "arm64",
                                "upgrade_available": False,
                            },
                            {
                                "name": "python3",
                                "current_version": "7.0-custom",
                                "arch": "amd64",
                                "upgrade_available": False,
                            },
                        ]
                    },
                },
            },
        )

        # Host C (other): Only has nginx
        self.host_other = Host.objects.create(
            fqdn="other.example.com",
            department="Operations",
            customer="external",
            archived=False,
            billable=True,
        )
        self._create_scan(
            self.host_other,
            {
                "version": artefact_registry.latest_version,
                "scan_date": self.now.isoformat(),
                "hostname": "other.example.com",
                "facts": {
                    "generic.HostnameCtl": {
                        "hostname": "other",
                        "os": "Ubuntu 22.04",
                    },
                    "generic.PackageManagerInfo": {
                        "installed_packages": [
                            {
                                "name": "nginx",
                                "current_version": "1.18.0",
                                "arch": "amd64",
                                "upgrade_available": False,
                            },
                        ]
                    },
                },
            },
        )

    def _create_scan(self, host: Host, data: dict):
        with mock.patch("django.utils.timezone.now", mock.Mock(return_value=self.now)):
            Scan.objects.create(host=host, data=data)
            host.last_scan_cache = data
            host.save()

    def test_positive_correlated_match(self):
        """match() returns the host where a single array item satisfies both conditions."""
        query_str = (
            "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
            "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0')"
        )
        ast = parse_query(query_str)
        result = list(search_hosts_by_scan_fields(Host.objects.all(), ast))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].fqdn, "matching.example.com")

    def test_case_insensitive_matching(self):
        """Pattern matching in match() is case-insensitive (ILIKE)."""
        query_str = (
            "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'PHP', "
            "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0')"
        )
        ast = parse_query(query_str)
        result = list(search_hosts_by_scan_fields(Host.objects.all(), ast))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].fqdn, "matching.example.com")

    def test_multi_pair_matching(self):
        """match() works across 3 pairs on the same array element."""
        # Host A has php7.0-cli with current_version 7.0... and arch amd64
        query_match = (
            "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
            "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0', "
            "facts.generic.PackageManagerInfo.installed_packages[].arch, 'amd64')"
        )
        ast = parse_query(query_match)
        result = list(search_hosts_by_scan_fields(Host.objects.all(), ast))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].fqdn, "matching.example.com")

        # Non-matching 3-pair: arch 'arm64' on php7.0 does not exist
        query_no_match = (
            "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
            "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0', "
            "facts.generic.PackageManagerInfo.installed_packages[].arch, 'arm64')"
        )
        ast_no = parse_query(query_no_match)
        result_no = list(search_hosts_by_scan_fields(Host.objects.all(), ast_no))
        self.assertEqual(len(result_no), 0)

    def test_negated_match(self):
        """NOT match(...) returns hosts not containing the correlated element."""
        query_str = (
            "NOT match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
            "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0')"
        )
        ast = parse_query(query_str)
        result = list(search_hosts_by_scan_fields(Host.objects.all(), ast).order_by("fqdn"))

        self.assertEqual(len(result), 2)
        fqdns = [h.fqdn for h in result]
        self.assertIn("split.example.com", fqdns)
        self.assertIn("other.example.com", fqdns)
        self.assertNotIn("matching.example.com", fqdns)

    def test_logical_and_composition(self):
        """match() composed with AND and other criteria."""
        query_str = (
            "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
            "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0') "
            "AND meta.department = 'Engineering'"
        )
        ast = parse_query(query_str)
        result = list(search_hosts_by_scan_fields(Host.objects.all(), ast))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].fqdn, "matching.example.com")

        # Mismatched AND condition
        query_str_miss = (
            "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
            "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0') "
            "AND meta.department = 'Operations'"
        )
        ast_miss = parse_query(query_str_miss)
        result_miss = list(search_hosts_by_scan_fields(Host.objects.all(), ast_miss))
        self.assertEqual(len(result_miss), 0)

    def test_logical_or_composition(self):
        """match() composed with OR returns union of matches."""
        query_str = (
            "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
            "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0') "
            "OR meta.fqdn = 'other.example.com'"
        )
        ast = parse_query(query_str)
        result = list(search_hosts_by_scan_fields(Host.objects.all(), ast).order_by("fqdn"))
        self.assertEqual(len(result), 2)
        fqdns = [h.fqdn for h in result]
        self.assertIn("matching.example.com", fqdns)
        self.assertIn("other.example.com", fqdns)

    def test_single_query_execution_count(self):
        """match() queries execute in exactly one SQL query."""
        queries = [
            # Standalone match
            (
                "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
                "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0')"
            ),
            # Negated match
            (
                "NOT match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
                "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0')"
            ),
            # Composite AND/OR query
            (
                "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
                "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0') "
                "OR meta.department = 'Operations'"
            ),
        ]
        for query_str in queries:
            with self.subTest(query=query_str):
                ast = parse_query(query_str)
                with CaptureQueriesContext(connection) as ctx:
                    list(search_hosts_by_scan_fields(Host.objects.all(), ast))
                self.assertEqual(len(ctx.captured_queries), 1)

    def test_language_spec_metadata(self):
        """get_language_spec accurately reflects match function details."""
        spec = get_language_spec()
        func_spec = next((f for f in spec["functions"] if f["name"] == "match"), None)
        self.assertIsNotNone(func_spec)
        self.assertEqual(func_spec["description"], MatchElements.description)
        self.assertEqual(func_spec["examples"], list(MatchElements.examples))
        self.assertEqual(func_spec["params"], [])
        self.assertEqual(len(func_spec["variadic"]), 2)
        self.assertEqual(func_spec["variadic"][0]["name"], "field")
        self.assertEqual(func_spec["variadic"][0]["cardinality"], Cardinality.ELEMENTS.value)
        self.assertEqual(func_spec["variadic"][0]["value_types"], [ValueType.STRING.value])
        self.assertEqual(func_spec["variadic"][1]["name"], "pattern")
        self.assertEqual(func_spec["variadic"][1]["cardinality"], Cardinality.SINGLE.value)
        self.assertEqual(func_spec["variadic"][1]["value_types"], [ValueType.STRING.value])
