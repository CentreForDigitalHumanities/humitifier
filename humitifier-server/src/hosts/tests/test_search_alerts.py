"""Comprehensive tests for alert search in advanced search."""

import csv
import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from humitifier_common.artefacts import registry as artefact_registry

from alerting.models import Alert, AlertAcknowledgment, AlertSeverity
from hosts.models import Host
from hosts.search import (
    ColumnSpec,
    derive_match_columns,
    evaluate_columns,
    format_value,
    get_language_spec,
    get_searchable_fields,
    parse_column,
    parse_query,
    search_hosts_by_scan_fields,
)
from hosts.search.constants import SearchFormParam, Section, ValueType

User = get_user_model()


class AlertSearchTestCase(TestCase):
    """Base test case setting up hosts with various alert states and scan data."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpassword123",
        )

        scan_cache_kvm = {
            "version": artefact_registry.latest_version,
            "facts": {
                "generic.HostnameCtl": {
                    "hostname": "srv-kvm-01",
                    "operating_system": "Ubuntu 22.04 LTS",
                    "kernel": "5.15.0-generic",
                    "architecture": "x86-64",
                    "virtualization": "kvm",
                },
            },
            "metrics": {},
            "errors": [],
        }

        scan_cache_baremetal = {
            "version": artefact_registry.latest_version,
            "facts": {
                "generic.HostnameCtl": {
                    "hostname": "srv-baremetal-01",
                    "operating_system": "Debian 12",
                    "kernel": "6.1.0-generic",
                    "architecture": "x86-64",
                    "virtualization": "none",
                },
            },
            "metrics": {},
            "errors": [],
        }

        # Host 1: Has active critical alert and active warning alert
        cls.host1 = Host.objects.create(
            fqdn="srv-kvm-01.example.com",
            department="Engineering",
            archived=False,
            billable=True,
            last_scan_cache=scan_cache_kvm,
        )
        cls.alert1_crit = Alert.objects.create(
            host=cls.host1,
            _creator="DiskUsageAlertGenerator",
            custom_identifier="/var",
            short_message="Disk space critical on /var",
            message="Partition /var is 95% full",
            severity=AlertSeverity.CRITICAL,
        )
        cls.alert1_warn = Alert.objects.create(
            host=cls.host1,
            _creator="MemoryAlertGenerator",
            custom_identifier="swap",
            short_message="High swap usage",
            message="Swap usage exceeds 80%",
            severity=AlertSeverity.WARNING,
        )

        # Host 2: Has acknowledged critical alert (using direct _alert FK)
        cls.host2 = Host.objects.create(
            fqdn="srv-baremetal-01.example.com",
            department="Operations",
            archived=False,
            billable=True,
            last_scan_cache=scan_cache_baremetal,
        )
        cls.alert2_crit = Alert.objects.create(
            host=cls.host2,
            _creator="DiskUsageAlertGenerator",
            custom_identifier="/var",
            short_message="Disk space critical on /var",
            message="Partition /var is 95% full",
            severity=AlertSeverity.CRITICAL,
        )
        cls.ack2 = AlertAcknowledgment.objects.create(
            _alert=cls.alert2_crit,
            host=cls.host2,
            _creator="DiskUsageAlertGenerator",
            custom_identifier="/var",
            acknowledged_by=cls.user,
            reason="Investigating large log files",
        )

        # Host 3: Has acknowledged alert linked by (host, _creator, custom_identifier) without _alert FK
        cls.host3 = Host.objects.create(
            fqdn="srv-legacy-01.example.com",
            department="Engineering",
            archived=True,
            billable=False,
            last_scan_cache=scan_cache_kvm,
        )
        cls.alert3_warn = Alert.objects.create(
            host=cls.host3,
            _creator="OutdatedOSAlertGenerator",
            custom_identifier="kernel",
            short_message="Outdated kernel installed",
            message="Running older kernel with security CVEs",
            severity=AlertSeverity.WARNING,
        )
        cls.ack3 = AlertAcknowledgment.objects.create(
            _alert=None,
            host=cls.host3,
            _creator="OutdatedOSAlertGenerator",
            custom_identifier="kernel",
            acknowledged_by=cls.user,
            reason="Decommission scheduled next week",
        )

        # Host 4: Zero alerts
        cls.host4 = Host.objects.create(
            fqdn="srv-clean-01.example.com",
            department="Engineering",
            archived=False,
            billable=True,
            last_scan_cache=scan_cache_kvm,
        )


class AlertFieldDiscoveryTests(TestCase):
    """Test field discovery and language spec exposure for alerts."""

    def test_alert_fields_discovered(self):
        fields = get_searchable_fields()
        alert_fields = [f for f in fields if f.section == Section.ALERTS]

        field_map = {f.id: f for f in alert_fields}
        self.assertIn("alerts[].severity", field_map)
        self.assertIn("alerts[].short_message", field_map)
        self.assertIn("alerts[].message", field_map)
        self.assertIn("alerts[].creator", field_map)
        self.assertIn("alerts[].custom_identifier", field_map)
        self.assertIn("alerts[].acknowledged", field_map)

        self.assertEqual(field_map["alerts[].severity"].value_type, ValueType.STRING)
        self.assertEqual(field_map["alerts[].acknowledged"].value_type, ValueType.BOOLEAN)

    def test_language_spec_includes_alerts(self):
        spec = get_language_spec()
        field_ids = [f["id"] for f in spec["fields"]]
        self.assertIn("alerts[].severity", field_ids)
        self.assertIn("alerts[].short_message", field_ids)
        self.assertIn("alerts[].acknowledged", field_ids)


class AlertQueryFilteringTests(AlertSearchTestCase):
    """Test query parsing and filtering against alert fields."""

    def test_search_by_severity(self):
        query = parse_query('alerts[].severity = "critical"')
        results = search_hosts_by_scan_fields(Host.objects.all(), query)
        # host1 has active critical; host2 has acknowledged critical; host3 warning; host4 none
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().fqdn, self.host1.fqdn)

    def test_search_by_short_message_contains(self):
        query = parse_query('alerts[].short_message CONTAINS "swap"')
        results = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().fqdn, self.host1.fqdn)

    def test_search_by_message_contains(self):
        query = parse_query('alerts[].message CONTAINS "95% full"')
        results = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().fqdn, self.host1.fqdn)

    def test_search_by_creator(self):
        query = parse_query('alerts[].creator = "MemoryAlertGenerator"')
        results = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().fqdn, self.host1.fqdn)

    def test_search_by_custom_identifier(self):
        query = parse_query('alerts[].custom_identifier = "/var"')
        results = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().fqdn, self.host1.fqdn)

    def test_default_unacknowledged_suppresses_acknowledged_alerts(self):
        # host2 has a critical alert but acknowledged -> should not match default query
        query = parse_query('alerts[].severity = "critical"')
        results = list(search_hosts_by_scan_fields(Host.objects.all(), query))
        self.assertIn(self.host1, results)
        self.assertNotIn(self.host2, results)

        # host3 has warning alert acknowledged by fallback join -> should not match
        query_warn = parse_query('alerts[].severity = "warning"')
        results_warn = list(search_hosts_by_scan_fields(Host.objects.all(), query_warn))
        self.assertIn(self.host1, results_warn)
        self.assertNotIn(self.host3, results_warn)

    def test_explicit_acknowledged_query(self):
        query_ack = parse_query("alerts[].acknowledged = true")
        results_ack = list(search_hosts_by_scan_fields(Host.objects.all(), query_ack))
        # host2 and host3 have acknowledged alerts
        self.assertIn(self.host2, results_ack)
        self.assertIn(self.host3, results_ack)
        self.assertNotIn(self.host1, results_ack)
        self.assertNotIn(self.host4, results_ack)

        query_unack = parse_query("alerts[].acknowledged = false")
        results_unack = list(search_hosts_by_scan_fields(Host.objects.all(), query_unack))
        # host1 has unacknowledged alerts
        self.assertIn(self.host1, results_unack)
        self.assertNotIn(self.host2, results_unack)

    def test_no_duplicate_hosts_when_multiple_alerts_match(self):
        # host1 has two alerts matching unacknowledged
        query = parse_query('alerts[].short_message CONTAINS "e"')  # "space" and "usage" both contain 'e'
        results = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().fqdn, self.host1.fqdn)

    def test_compound_query_meta_and_alert(self):
        query = parse_query('meta.department = "Engineering" AND alerts[].severity = "critical"')
        results = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().fqdn, self.host1.fqdn)

        # Non-matching department
        query_no_match = parse_query('meta.department = "Operations" AND alerts[].severity = "critical"')
        results_no_match = search_hosts_by_scan_fields(Host.objects.all(), query_no_match)
        self.assertEqual(results_no_match.count(), 0)

    def test_compound_query_facts_and_alert(self):
        query = parse_query(
            'facts.generic.HostnameCtl.virtualization = "kvm" AND alerts[].severity = "critical"'
        )
        results = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().fqdn, self.host1.fqdn)

    def test_count_alerts_aggregation(self):
        query = parse_query("count(alerts[].severity) > 0")
        results = list(search_hosts_by_scan_fields(Host.objects.all(), query))
        self.assertIn(self.host1, results)
        self.assertNotIn(self.host2, results)
        self.assertNotIn(self.host3, results)
        self.assertNotIn(self.host4, results)


class AlertColumnEvaluationTests(AlertSearchTestCase):
    """Test column projection, matching derivation, and formatting for alert fields."""

    def test_column_evaluation_active_alerts(self):
        cols = [
            parse_column("alerts[].severity"),
            parse_column("alerts[].short_message"),
            parse_column("alerts[].creator"),
        ]
        results = evaluate_columns(Host.objects.all(), cols)
        res_by_fqdn = {r["object"].fqdn: r["fields"] for r in results}

        # host1: active critical and warning
        h1_fields = res_by_fqdn[self.host1.fqdn]
        self.assertIn("critical", h1_fields["alerts[].severity"])
        self.assertIn("warning", h1_fields["alerts[].severity"])
        self.assertIn("Disk space critical on /var", h1_fields["alerts[].short_message"])
        self.assertIn("High swap usage", h1_fields["alerts[].short_message"])

        # host2: all alerts acknowledged -> empty array
        h2_fields = res_by_fqdn[self.host2.fqdn]
        self.assertEqual(h2_fields["alerts[].severity"], [])
        self.assertEqual(h2_fields["alerts[].short_message"], [])

        # host4: no alerts -> empty array
        h4_fields = res_by_fqdn[self.host4.fqdn]
        self.assertEqual(h4_fields["alerts[].severity"], [])

    def test_column_evaluation_acknowledged_field(self):
        cols = [parse_column("alerts[].acknowledged")]
        results = evaluate_columns(Host.objects.all(), cols)
        res_by_fqdn = {r["object"].fqdn: r["fields"] for r in results}

        # host1 has 2 unacknowledged alerts
        self.assertEqual(res_by_fqdn[self.host1.fqdn]["alerts[].acknowledged"], [False, False])
        # host2 has 1 acknowledged alert
        self.assertEqual(res_by_fqdn[self.host2.fqdn]["alerts[].acknowledged"], [True])
        # host3 has 1 acknowledged alert (fallback link)
        self.assertEqual(res_by_fqdn[self.host3.fqdn]["alerts[].acknowledged"], [True])
        # host4 has 0 alerts
        self.assertEqual(res_by_fqdn[self.host4.fqdn]["alerts[].acknowledged"], [])

    def test_column_with_alias(self):
        col = parse_column('alerts[].severity AS "Active Severities"')
        self.assertEqual(col.label, "Active Severities")

        results = evaluate_columns(Host.objects.filter(pk=self.host1.pk), [col])
        self.assertIn("Active Severities", results[0]["fields"])

    def test_derive_match_columns(self):
        query = parse_query('alerts[].severity = "critical"')
        match_cols = derive_match_columns(query)
        self.assertEqual(len(match_cols), 1)
        self.assertEqual(match_cols[0].label, 'Matches: alerts[].severity = "critical"')

        results = evaluate_columns(Host.objects.all(), match_cols)
        res_by_fqdn = {r["object"].fqdn: r["fields"] for r in results}

        # host1 matches
        self.assertEqual(
            res_by_fqdn[self.host1.fqdn]['Matches: alerts[].severity = "critical"'],
            ["critical"],
        )
        # host2 (acknowledged) and host4 (none) do not match
        self.assertEqual(
            res_by_fqdn[self.host2.fqdn]['Matches: alerts[].severity = "critical"'],
            [],
        )
        self.assertEqual(
            res_by_fqdn[self.host4.fqdn]['Matches: alerts[].severity = "critical"'],
            [],
        )

    def test_format_value_for_alerts(self):
        self.assertEqual(format_value(["critical", "warning"]), "critical, warning")
        self.assertEqual(format_value([False, True]), "False, True")
        self.assertEqual(format_value([]), "")


class AlertSearchExportIntegrationTests(AlertSearchTestCase):
    """Test full HTTP view request flow with CSV and JSON exports for alert columns."""

    def setUp(self):
        self.client.force_login(self.user)

    def test_export_csv_with_alert_columns(self):
        url = reverse("hosts:advanced_search")
        post_data = {
            SearchFormParam.SEARCH_STRING: 'alerts[].severity = "critical"',
            SearchFormParam.COLUMNS: "alerts[].severity,alerts[].short_message",
            "export-csv": "true",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")

        csv_content = response.content.decode("utf-8")
        reader = csv.DictReader(StringIO(csv_content))
        rows = list(reader)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["FQDN"], self.host1.fqdn)
        self.assertIn("critical", row["alerts[].severity"])
        self.assertIn("Disk space critical on /var", row["alerts[].short_message"])

    def test_export_json_with_alert_columns(self):
        url = reverse("hosts:advanced_search")
        post_data = {
            SearchFormParam.SEARCH_STRING: 'alerts[].severity = "critical"',
            SearchFormParam.COLUMNS: "alerts[].severity,alerts[].short_message",
            "export-json": "true",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        json_data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(json_data), 1)
        row = json_data[0]
        self.assertEqual(row["FQDN"], self.host1.fqdn)
        self.assertIn("critical", row["alerts[].severity"])
        self.assertIn("Disk space critical on /var", row["alerts[].short_message"])
