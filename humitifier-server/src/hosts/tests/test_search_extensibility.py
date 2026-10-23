"""Tests for search architecture extensibility, single-query OR, and correlated predicates."""

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
from hosts.search.functions.base import Param, ParamKind, SearchFunction
from hosts.search.functions.registry import function_registry
from hosts.search.nodes import ExprType
from hosts.search.sql import CompileContext, SqlFragment


class MatchElements(SearchFunction):
    """Test-only correlated predicate matching multiple fields on the same array element."""

    name = "match"
    description = "Test correlated match across multiple fields of the same array element"
    examples = ("match(arr[].name, 'php', arr[].version, '7.0')",)
    params = ()
    variadic = (
        Param("field", ParamKind.FIELD, frozenset({ValueType.STRING}), Cardinality.ELEMENTS),
        Param("pattern", ParamKind.LITERAL, frozenset({ValueType.STRING}), Cardinality.SINGLE),
    )

    @classmethod
    def validate(cls, args):
        super().validate(args)
        first_field = args[0].field
        for i in range(0, len(args), 2):
            f = args[i].field
            if (f.section, f.artefact_key, f.array_path) != (
                first_field.section,
                first_field.artefact_key,
                first_field.array_path,
            ):
                raise ValueError(
                    f"All fields in '{cls.name}' must belong to the same array at position {args[i].position}"
                )

    @classmethod
    def return_type(cls, args):
        return ExprType(ValueType.BOOLEAN, Cardinality.SINGLE)

    @classmethod
    def compile(cls, args, ctx: CompileContext):
        first_field = args[0].field
        source = ctx.get_element_source(first_field)
        conditions = []
        for i in range(0, len(args), 2):
            f = args[i].field
            pattern = args[i + 1].value
            val = ctx.element_value(f, source)
            conditions.append(
                SqlFragment(f"{val.sql} ILIKE %s", val.params + (f"%{pattern}%",))
            )
        where_parts = [source.type_check] + conditions
        where_joined = SqlFragment.join(" AND ", where_parts)
        sql = f"EXISTS (SELECT 1 FROM {source.from_clause.sql} WHERE {where_joined.sql})"
        return SqlFragment(sql, source.from_clause.params + where_joined.params)


class SearchExtensibilityTestCase(TestCase):
    """Test extensible function registration and correlated combined array lookups."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        function_registry.unregister(MatchElements)

    def setUp(self):
        self.now = timezone.now()

        # Host A: One package has BOTH name "php" and current_version "7.0"
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
                        "os": "Ubuntu 22.04",
                    },
                    "generic.PackageManagerInfo": {
                        "installed_packages": [
                            {
                                "name": "php7.0-cli",
                                "current_version": "7.0.33-0ubuntu0.16.04.16",
                                "upgrade_available": False,
                            },
                            {
                                "name": "apache2",
                                "current_version": "2.4.52",
                                "upgrade_available": False,
                            },
                        ]
                    },
                },
            },
        )

        # Host B: Name "php" is on one package, current_version "7.0" is on a DIFFERENT package
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
                                "upgrade_available": False,
                            },
                            {
                                "name": "python3",
                                "current_version": "7.0-custom",
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

    def test_auto_registration_in_language_spec(self):
        """A SearchFunction subclass is automatically registered and appears in get_language_spec."""
        spec = get_language_spec()
        func_names = [f["name"] for f in spec["functions"]]
        self.assertIn("match", func_names)

        match_spec = next(f for f in spec["functions"] if f["name"] == "match")
        self.assertEqual(match_spec["description"], MatchElements.description)
        self.assertIsNotNone(match_spec["variadic"])
        self.assertEqual(len(match_spec["variadic"]), 2)

    def test_correlated_predicate_matches_same_element_only(self):
        """Correlated predicate matches only hosts where one element satisfies all partial criteria."""
        query_str = (
            "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
            "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0')"
        )
        ast = parse_query(query_str)
        result = list(search_hosts_by_scan_fields(Host.objects.all(), ast))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].fqdn, "matching.example.com")

    def test_single_query_for_complex_or(self):
        """OR query across meta, scalar, and array fields executes as a single SQL query."""
        query_str = (
            'meta.department = "IT" OR '
            'facts.generic.HostnameCtl.os contains "Debian" OR '
            'facts.generic.PackageManagerInfo.installed_packages[].name = "apache2"'
        )
        ast = parse_query(query_str)

        with CaptureQueriesContext(connection) as ctx:
            result = list(search_hosts_by_scan_fields(Host.objects.all(), ast))

        # Must execute in exactly 1 query, not multiple roundtrips or ID materialization
        self.assertEqual(len(ctx.captured_queries), 1)
        self.assertEqual(len(result), 2)
