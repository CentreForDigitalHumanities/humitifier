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

    def test_validation_type_mismatch_boolean_with_string(self):
        """Passing a string literal for a boolean array field raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            parse_query(
                "match("
                "facts.generic.PackageManagerInfo.installed_packages[].upgrade_available, 'true'"
                ")"
            )
        self.assertIn("Type mismatch: cannot match boolean field with string literal", str(ctx.exception))

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

    def test_validation_type_mismatch_string_with_integer(self):
        """Passing an integer literal for a string array field raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            parse_query(
                "match(facts.generic.PackageManagerInfo.installed_packages[].name, 123)"
            )
        self.assertIn("Type mismatch: cannot match string field with integer literal", str(ctx.exception))

    def test_validation_type_mismatch_integer_with_boolean(self):
        """Passing a boolean literal for an integer array field raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            parse_query(
                "match(facts.generic.Hardware.memory[].size, true)"
            )
        self.assertIn("Type mismatch: cannot match integer field with boolean literal", str(ctx.exception))

    def test_validation_null_literal_pattern(self):
        """Passing a null literal for pattern raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            parse_query(
                "match(facts.generic.PackageManagerInfo.installed_packages[].name, null)"
            )
        self.assertIn("requires an boolean/integer/string field, got null", str(ctx.exception))


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
                    "generic.Hardware": {
                        "num_cpus": 4,
                        "memory": [
                            {
                                "range": "0-1",
                                "size": 2147483648,
                                "state": "online",
                                "removable": False,
                                "block": "0",
                            }
                        ],
                        "block_devices": [],
                        "pci_devices": [],
                        "usb_devices": [],
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
                                "upgrade_available": True,
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
                    "generic.Hardware": {
                        "num_cpus": 2,
                        "memory": [
                            {
                                "range": "0-1",
                                "size": 1073741824,
                                "state": "online",
                                "removable": True,
                                "block": "1",
                            }
                        ],
                        "block_devices": [],
                        "pci_devices": [],
                        "usb_devices": [],
                    },
                    "generic.PackageManagerInfo": {
                        "installed_packages": [
                            {
                                "name": "php8.1",
                                "current_version": "8.1.2-1ubuntu2",
                                "arch": "arm64",
                                "upgrade_available": True,
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
                    "generic.Hardware": {
                        "num_cpus": 1,
                        "memory": [
                            {
                                "range": "0-1",
                                "size": 2147483648,
                                "state": "offline",
                                "removable": True,
                                "block": "2",
                            }
                        ],
                        "block_devices": [],
                        "pci_devices": [],
                        "usb_devices": [],
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

    def test_boolean_matching(self):
        """match() works with boolean fields on array elements."""
        # Host A has php7.0-cli with upgrade_available=False
        query_false = (
            "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
            "facts.generic.PackageManagerInfo.installed_packages[].upgrade_available, false)"
        )
        ast_false = parse_query(query_false)
        res_false = list(search_hosts_by_scan_fields(Host.objects.all(), ast_false))
        self.assertEqual(len(res_false), 1)
        self.assertEqual(res_false[0].fqdn, "matching.example.com")

        # Host B has php8.1 with upgrade_available=True
        query_true = (
            "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
            "facts.generic.PackageManagerInfo.installed_packages[].upgrade_available, true)"
        )
        ast_true = parse_query(query_true)
        res_true = list(search_hosts_by_scan_fields(Host.objects.all(), ast_true))
        self.assertEqual(len(res_true), 1)
        self.assertEqual(res_true[0].fqdn, "split.example.com")

        # Neither host has nginx with upgrade_available=True
        query_none = (
            "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'nginx', "
            "facts.generic.PackageManagerInfo.installed_packages[].upgrade_available, true)"
        )
        ast_none = parse_query(query_none)
        res_none = list(search_hosts_by_scan_fields(Host.objects.all(), ast_none))
        self.assertEqual(len(res_none), 0)

    def test_integer_matching(self):
        """match() works with integer fields on array elements."""
        # Host A has memory size 2147483648 and block '0'
        query_match_a = (
            "match(facts.generic.Hardware.memory[].size, 2147483648, "
            "facts.generic.Hardware.memory[].block, '0')"
        )
        ast_a = parse_query(query_match_a)
        res_a = list(search_hosts_by_scan_fields(Host.objects.all(), ast_a))
        self.assertEqual(len(res_a), 1)
        self.assertEqual(res_a[0].fqdn, "matching.example.com")

        # Host C has memory size 2147483648 and block '2'
        query_match_c = (
            "match(facts.generic.Hardware.memory[].size, 2147483648, "
            "facts.generic.Hardware.memory[].block, '2')"
        )
        ast_c = parse_query(query_match_c)
        res_c = list(search_hosts_by_scan_fields(Host.objects.all(), ast_c))
        self.assertEqual(len(res_c), 1)
        self.assertEqual(res_c[0].fqdn, "other.example.com")

        # Host B has memory size 1073741824 and block '1'
        query_match_b = (
            "match(facts.generic.Hardware.memory[].size, 1073741824, "
            "facts.generic.Hardware.memory[].block, '1')"
        )
        ast_b = parse_query(query_match_b)
        res_b = list(search_hosts_by_scan_fields(Host.objects.all(), ast_b))
        self.assertEqual(len(res_b), 1)
        self.assertEqual(res_b[0].fqdn, "split.example.com")

    def test_mixed_types_matching(self):
        """match() works with combined string, integer, and boolean fields on array elements."""
        query = (
            "match(facts.generic.Hardware.memory[].size, 2147483648, "
            "facts.generic.Hardware.memory[].block, '0', "
            "facts.generic.Hardware.memory[].removable, false)"
        )
        ast = parse_query(query)
        res = list(search_hosts_by_scan_fields(Host.objects.all(), ast))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].fqdn, "matching.example.com")

        # Host A has removable=False, so matching with removable=true returns empty
        query_miss = (
            "match(facts.generic.Hardware.memory[].size, 2147483648, "
            "facts.generic.Hardware.memory[].block, '0', "
            "facts.generic.Hardware.memory[].removable, true)"
        )
        ast_miss = parse_query(query_miss)
        res_miss = list(search_hosts_by_scan_fields(Host.objects.all(), ast_miss))
        self.assertEqual(len(res_miss), 0)

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
            # Boolean and integer match
            (
                "match(facts.generic.Hardware.memory[].size, 2147483648, "
                "facts.generic.Hardware.memory[].removable, false)"
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
        self.assertEqual(
            func_spec["variadic"][0]["value_types"],
            ["boolean", "integer", "string"],
        )
        self.assertEqual(func_spec["variadic"][1]["name"], "pattern")
        self.assertEqual(func_spec["variadic"][1]["cardinality"], Cardinality.SINGLE.value)
        self.assertEqual(
            func_spec["variadic"][1]["value_types"],
            ["boolean", "integer", "string"],
        )
