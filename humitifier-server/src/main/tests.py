from django.test import TestCase
from django.urls import reverse

from alerting.models import Alert, AlertSeverity
from hosts.models import DataSource, Host
from main.models import User


class DashboardStatsFilterTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.client.force_login(self.user)

        self.ds = DataSource.objects.create(name="Puppet")
        self.host1 = Host.objects.create(
            fqdn="server1.example.com",
            customer="Acme",
            otap_stage="production",
            data_source=self.ds,
            last_scan_cache={
                "facts": {
                    "generic.HostnameCtl": {
                        "os": "Ubuntu 22.04"
                    }
                }
            },
        )
        self.alert1 = Alert.objects.create(
            host=self.host1,
            _creator="test",
            severity=AlertSeverity.INFO,
            short_message="Disk full",
            message="Disk / is full",
        )

    def test_dashboard_stat_links_without_filters(self):
        response = self.client.get(reverse("main:dashboard"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        self.assertIn("?severity=info#alerts", content)
        self.assertIn("otap_stage=production", content)
        self.assertIn("os=%22Ubuntu+22.04%22", content)
        self.assertIn("customer=Acme", content)
        self.assertIn(f"data_source={self.ds.id}", content)

    def test_dashboard_stat_links_preserve_existing_filters(self):
        # User has filters enabled on stats: customer=Acme
        response = self.client.get(reverse("main:dashboard"), {"customer": "Acme"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        # Alerts chart links preserve customer filter
        self.assertIn("customer=Acme&severity=info#alerts", content)

        # Alert type chart links preserve customer filter
        self.assertIn("customer=Acme&type=Disk+full#alerts", content)

        # OTAP chart link preserves customer filter
        self.assertIn("customer=Acme&otap_stage=production", content)

        # OS chart link preserves customer filter
        self.assertIn("customer=Acme&os=%22Ubuntu+22.04%22", content)

        # Data source chart link preserves customer filter
        self.assertIn(f"customer=Acme&data_source={self.ds.id}", content)

    def test_dashboard_stat_links_isolate_host_list_filters(self):
        # Create additional alerts so page=2 is valid on dashboard (paginate_by = 50)
        alerts = [
            Alert(
                host=self.host1,
                _creator="test",
                severity=AlertSeverity.INFO,
                short_message="Disk full",
                message=f"Disk / is full {i}",
            )
            for i in range(55)
        ]
        Alert.objects.bulk_create(alerts)

        # User has alert filter and pagination active on dashboard: severity=info, type="Disk full", page=2, customer=Acme
        response = self.client.get(
            reverse("main:dashboard"),
            {"severity": "info", "type": "Disk full", "page": "2", "customer": "Acme"},
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        # Dashboard alert links keep dashboard filter names (severity, type, customer)
        self.assertIn("severity=warning&type=Disk+full&page=2&customer=Acme#alerts", content)

        # Host list links preserve only stats filters (customer=Acme) plus the stat dimension,
        # without leaking alert filters (severity, type) or alert pagination (page=2)
        self.assertIn(
            "'/hosts/?customer=Acme&otap_stage=production'",
            content,
        )
        self.assertIn(
            "'/hosts/?customer=Acme&os=%22Ubuntu+22.04%22'",
            content,
        )
        self.assertIn(
            f"'/hosts/?customer=Acme&data_source={self.ds.id}'",
            content,
        )


class TemplateTagsTest(TestCase):
    def test_param_replace_tag(self):
        from django.test import RequestFactory
        from main.templatetags.param_replace import param_replace

        factory = RequestFactory()
        request = factory.get("/dashboard/?severity=info&page=2")
        context = {"request": request}

        # Adding or updating a parameter
        result = param_replace(context, severity="warning")
        self.assertIn("severity=warning", result)
        self.assertIn("page=2", result)

        # Removing a parameter by setting empty string
        result_empty = param_replace(context, severity="", page="")
        self.assertEqual(result_empty, "")

    def test_filter_params_tag(self):
        from django.test import RequestFactory
        from main.filters import StatsFilters
        from main.templatetags.param_replace import filter_params

        factory = RequestFactory()
        # Request has customer and os (which belong to StatsFilters) plus unrelated GET params
        request = factory.get("/dashboard/?customer=Acme&os=Ubuntu+22.04&severity=critical&page=3&foo=bar")
        filterset = StatsFilters(request.GET, queryset=Host.objects.all())

        # Calling filter_params extracts only StatsFilters fields (customer, os) and adds otap_stage
        result = filter_params(filterset, otap_stage="production")
        from urllib.parse import parse_qs

        parsed = parse_qs(result)
        self.assertEqual(
            parsed,
            {
                "customer": ["Acme"],
                "os": ["Ubuntu 22.04"],
                "otap_stage": ["production"],
            },
        )

        # Overriding an existing filterset field
        result_override = filter_params(filterset, customer="Beta")
        parsed_override = parse_qs(result_override)
        self.assertEqual(
            parsed_override,
            {
                "customer": ["Beta"],
                "os": ["Ubuntu 22.04"],
            },
        )

        # Passing None or empty filterset
        result_empty = filter_params(None, otap_stage="test")
        self.assertEqual(result_empty, "otap_stage=test")
