from datetime import datetime, timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from hosts.models import Host, Scan
from hosts.utils import historical_clean


# Create your tests here.
class HistoricalCleanTests(TestCase):

    def setUp(self):
        self.host = Host.objects.create(
            fqdn="test",
        )
        self.now = timezone.now()

    def _create_scan_with_date(self, dt: datetime, host=None):
        if host is None:
            host = self.host

        with mock.patch('django.utils.timezone.now', mock.Mock(return_value=dt)):
            Scan.objects.create(
                host=host,
                data={}
            )

    def test_keep_all_daily(self):
        self._create_scan_with_date(self.now)
        self._create_scan_with_date(self.now - timedelta(seconds=1))
        self._create_scan_with_date(self.now - timedelta(seconds=2))

        self.assertEqual(self.host.scans.count(), 3)

        historical_clean()

        self.assertEqual(self.host.scans.count(), 3)

    def test_keep_all_daily_multiple_hosts(self):
        def _create_scans(host=None):
            self._create_scan_with_date(self.now, host=host)
            self._create_scan_with_date(self.now - timedelta(seconds=1), host=host)
            self._create_scan_with_date(self.now - timedelta(seconds=2), host=host)

        host2 = Host.objects.create(
            fqdn="test2",
        )

        _create_scans()
        _create_scans(host2)

        self.assertEqual(self.host.scans.count(), 3)
        self.assertEqual(host2.scans.count(), 3)

        historical_clean()

        self.assertEqual(self.host.scans.count(), 3)
        self.assertEqual(host2.scans.count(), 3)

    def test_reduce_weekly(self):
        self._create_scan_with_date(self.now)
        self._create_scan_with_date(self.now - timedelta(days=1, seconds=2))
        self._create_scan_with_date(self.now - timedelta(days=1, seconds=4))
        self._create_scan_with_date(self.now - timedelta(days=2, seconds=2))
        self._create_scan_with_date(self.now - timedelta(days=2, seconds=4))

        self.assertEqual(self.host.scans.count(), 5)

        historical_clean()

        self.assertEqual(self.host.scans.count(), 3)

    def test_reduce_weekly_multiple_hosts (self):
        def _create_scans(host=None):
            self._create_scan_with_date(self.now, host=host)
            self._create_scan_with_date(self.now - timedelta(days=1, seconds=2), host=host)
            self._create_scan_with_date(self.now - timedelta(days=1, seconds=4), host=host)
            self._create_scan_with_date(self.now - timedelta(days=2, seconds=2), host=host)
            self._create_scan_with_date(self.now - timedelta(days=2, seconds=4), host=host)

        host2 = Host.objects.create(
            fqdn="test2",
        )
        _create_scans()
        _create_scans(host2)

        self.assertEqual(self.host.scans.count(), 5)
        self.assertEqual(host2.scans.count(), 5)

        historical_clean()

        self.assertEqual(self.host.scans.count(), 3)
        self.assertEqual(host2.scans.count(), 3)

    def test_reduce_monthly(self):
        self._create_scan_with_date(self.now)
        self._create_scan_with_date(self.now - timedelta(days=31, seconds=2))
        self._create_scan_with_date(self.now - timedelta(days=31, seconds=4))
        self._create_scan_with_date(self.now - timedelta(days=62, seconds=2))
        self._create_scan_with_date(self.now - timedelta(days=62, seconds=4))
        self._create_scan_with_date(self.now - timedelta(days=700, seconds=2))
        self._create_scan_with_date(self.now - timedelta(days=700, seconds=4))

        self.assertEqual(self.host.scans.count(), 7)

        historical_clean()

        self.assertEqual(self.host.scans.count(), 4)

    def test_reduce_monthly_multiple_hosts (self):
        def _create_scans(host=None):
            self._create_scan_with_date(self.now, host=host)
            self._create_scan_with_date(self.now - timedelta(days=31, seconds=2), host=host)
            self._create_scan_with_date(self.now - timedelta(days=31, seconds=4), host=host)
            self._create_scan_with_date(self.now - timedelta(days=62, seconds=2), host=host)
            self._create_scan_with_date(self.now - timedelta(days=62, seconds=4), host=host)
            self._create_scan_with_date(self.now - timedelta(days=700, seconds=2),
                                        host=host)
            self._create_scan_with_date(self.now - timedelta(days=700, seconds=4), host=host)

        host2 = Host.objects.create(
            fqdn="test2",
        )
        _create_scans()
        _create_scans(host2)

        self.assertEqual(self.host.scans.count(), 7)
        self.assertEqual(host2.scans.count(), 7)

        historical_clean()

        self.assertEqual(self.host.scans.count(), 4)
        self.assertEqual(host2.scans.count(), 4)

    def test_all(self):
        # Today = 3 / 3
        self._create_scan_with_date(self.now)
        self._create_scan_with_date(self.now - timedelta(seconds=2))
        self._create_scan_with_date(self.now - timedelta(seconds=4))
        # Yesterday = 1 / 3
        self._create_scan_with_date(self.now - timedelta(days=1, seconds=2))
        self._create_scan_with_date(self.now - timedelta(days=1, seconds=4))
        self._create_scan_with_date(self.now - timedelta(days=1, seconds=6))
        # 2 months ago = 1 / 2
        self._create_scan_with_date(self.now - timedelta(days=60, seconds=2))
        self._create_scan_with_date(self.now - timedelta(days=60, seconds=4))
        # 4 months ago = 1 / 3
        self._create_scan_with_date(self.now - timedelta(days=120, seconds=2))
        self._create_scan_with_date(self.now - timedelta(days=120, seconds=4))
        self._create_scan_with_date(self.now - timedelta(days=120, seconds=6))


        self.assertEqual(self.host.scans.count(), 11)

        historical_clean()

        self.assertEqual(self.host.scans.count(), 6)
