from datetime import date, datetime, timezone
from decimal import Decimal
from django.test import TestCase
from hosts.models import Host, Scan
from reporting.models import CostsScheme
from reporting.utils.costs_excel_export import create_timeseries_cost_excel


class MultiPlatformCostsTestCase(TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 1, tzinfo=timezone.utc)

        # Create schemes for same group but different platforms
        self.scheme_vmware = CostsScheme.objects.create(
            name="2026",
            platform="vmware",
            cpu=Decimal("10.00"),
            memory=Decimal("2.00"),
            storage=Decimal("50.00"),  # per TB
            linux=Decimal("5.00"),
            windows=Decimal("15.00"),
            management=Decimal("100.00"),
        )

        self.scheme_azure = CostsScheme.objects.create(
            name="2026",
            platform="microsoft",  # Microsoft is the ID for Hyper-V/Azure usually in systemd-detect-virt
            cpu=Decimal("20.00"),
            memory=Decimal("4.00"),
            storage=Decimal("100.00"),
            linux=Decimal("0.00"),
            windows=Decimal("0.00"),
            management=Decimal("50.00"),
        )

        # Host 1: VMware
        self.host_vmware = Host.objects.create(
            fqdn="vmware-host.example.com", billable=True, customer="TestCustomer"
        )
        self._create_scan(
            self.host_vmware, "vmware", 2, 4, 100
        )  # 2 CPU, 4GB RAM, 100GB Disk

        # Host 2: Azure
        self.host_azure = Host.objects.create(
            fqdn="azure-host.example.com", billable=True, customer="TestCustomer"
        )
        self._create_scan(
            self.host_azure, "microsoft", 2, 4, 100
        )  # 2 CPU, 4GB RAM, 100GB Disk

    def _create_scan(self, host, virtualization, cpus, memory_gb, disk_gb):
        scan_data = {
            "version": 2,
            "scan_date": self.now.isoformat(),
            "hostname": host.fqdn,
            "original_input": {
                "hostname": host.fqdn,
                "artefacts": {},
            },
            "facts": {
                "generic.HostnameCtl": {
                    "hostname": host.fqdn.split(".")[0],
                    "os": "Ubuntu 22.04 LTS",
                    "cpe_os_name": "cpe:/o:canonical:ubuntu_linux:22.04",
                    "kernel": "5.15.0",
                    "virtualization": virtualization,
                },
                "generic.Hardware": {
                    "num_cpus": cpus,
                    "memory": [
                        {
                            "range": "0x0-0x1",
                            "size": memory_gb * 1024 * 1024 * 1024,
                            "state": "online",
                            "removable": False,
                            "block": "0",
                        }
                    ],
                    "block_devices": [
                        {
                            "name": "sda",
                            "type": "disk",
                            "size": f"{disk_gb}G",
                            "model": "Test Disk",
                        }
                    ],
                    "pci_devices": [],
                    "usb_devices": [],
                },
            },
            "metrics": {},
            "errors": [],
        }
        Scan.objects.create(host=host, data=scan_data)
        host.last_scan_cache = scan_data
        host.last_scan_date = self.now
        host.save()

    def test_multi_platform_report(self):
        # Prepare schemes dict like the task does
        schemes_by_platform = {
            "vmware": self.scheme_vmware,
            "microsoft": self.scheme_azure,
        }

        start_date = date(2026, 8, 1)
        end_date = date(2026, 8, 1)

        excel_buffer = create_timeseries_cost_excel(
            schemes_by_platform,
            "test_report.xlsx",
            start_date,
            end_date,
            customers=["TestCustomer"],
        )

        # Verify the calculation logic directly.
        from reporting.utils.get_server_hardware import get_hardware_fact
        from reporting.utils.cost_calculations import calculate_from_hardware_artefact

        # VMware check
        scan_vmware = self.host_vmware.scans.first().get_scan_object()
        info_vmware = get_hardware_fact(scan_vmware)
        self.assertEqual(info_vmware.platform, "vmware")
        costs_vmware = calculate_from_hardware_artefact(
            info_vmware.hardware, self.scheme_vmware, os=info_vmware.os
        )

        # CPU: 2 * 10 = 20
        # Memory: 4 * 2 = 8
        # OS: Linux = 5
        # Storage: 100 * (50/1024) = 4.8828...
        # Management: 100

        self.assertEqual(costs_vmware.cpu, Decimal("20.00"))
        self.assertEqual(costs_vmware.memory, Decimal("8.00"))
        self.assertEqual(costs_vmware.os, Decimal("5.00"))
        self.assertAlmostEqual(costs_vmware.storage, Decimal("4.88"), places=2)

        # Azure check
        scan_azure = self.host_azure.scans.first().get_scan_object()
        info_azure = get_hardware_fact(scan_azure)
        self.assertEqual(info_azure.platform, "microsoft")
        costs_azure = calculate_from_hardware_artefact(
            info_azure.hardware, self.scheme_azure, os=info_azure.os
        )

        # CPU: 2 * 20 = 40
        # Memory: 4 * 4 = 16
        # OS: 0
        # Storage: 100 * (100/1024) = 9.7656...
        # Management: 50

        self.assertEqual(costs_azure.cpu, Decimal("40.00"))
        self.assertEqual(costs_azure.memory, Decimal("16.00"))
        self.assertEqual(costs_azure.os, Decimal("0.00"))
        self.assertAlmostEqual(costs_azure.storage, Decimal("9.77"), places=2)

    def test_platform_change_between_months(self):
        # Host that changes from vmware to microsoft
        host = Host.objects.create(
            fqdn="changing-host.example.com", billable=True, customer="TestCustomer"
        )
        # Manually set created_at to be before our test months
        Host.objects.filter(pk=host.pk).update(
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        host.refresh_from_db()

        # Month 1: VMware
        month1 = datetime(2026, 8, 1, tzinfo=timezone.utc)
        self._create_scan_at_time(host, "vmware", 2, 4, 100, month1)

        # Month 2: Azure
        month2 = datetime(2026, 9, 1, tzinfo=timezone.utc)
        self._create_scan_at_time(host, "microsoft", 2, 4, 100, month2)

        schemes_by_platform = {
            "vmware": self.scheme_vmware,
            "microsoft": self.scheme_azure,
        }

        start_date = date(2026, 8, 1)
        end_date = date(2026, 9, 1)

        # This will trigger create_timeseries_cost_excel
        # We can't easily check the logic it uses
        from reporting.utils.costs_excel_export import _get_server_info_for_month

        info1 = _get_server_info_for_month(host, month1)
        self.assertEqual(info1.platform, "vmware")

        info2 = _get_server_info_for_month(host, month2)
        self.assertEqual(info2.platform, "microsoft")

    def test_explicit_multiple_schemes_selection(self):
        # This tests the new logic where we select multiple schemes in the form
        from reporting.tasks import generate_cost_report
        from reporting.models import GeneratedReport
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_superuser(
            username="admin_test", password="password", email="admin_test@example.com"
        )
        report = GeneratedReport.objects.create(
            filename="test_multi.xlsx",
            created_by=user,
            customers=[],
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 1),
        )

        # In the new logic, we pass a list of IDs
        scheme_ids = [self.scheme_vmware.pk, self.scheme_azure.pk]

        start_date = "2026-08-01"
        end_date = "2026-08-01"

        # We call the task directly (not .delay) to test its internal logic
        generate_cost_report(
            report.pk,
            scheme_ids,
            "test_multi.xlsx",
            start_date,
            end_date,
            ["TestCustomer"],
        )

        report.refresh_from_db()
        self.assertEqual(report.status, GeneratedReport.Status.COMPLETED)
        self.assertTrue(report.file.size > 0)

    def _create_scan_at_time(
        self, host, virtualization, cpus, memory_gb, disk_gb, time
    ):
        scan_data = {
            "version": 2,
            "scan_date": time.isoformat(),
            "hostname": host.fqdn,
            "original_input": {
                "hostname": host.fqdn,
                "artefacts": {},
            },
            "facts": {
                "generic.HostnameCtl": {
                    "hostname": host.fqdn.split(".")[0],
                    "os": "Ubuntu 22.04 LTS",
                    "cpe_os_name": "cpe:/o:canonical:ubuntu_linux:22.04",
                    "kernel": "5.15.0",
                    "virtualization": virtualization,
                },
                "generic.Hardware": {
                    "num_cpus": cpus,
                    "memory": [
                        {
                            "range": "0x0-0x1",
                            "size": memory_gb * 1024 * 1024 * 1024,
                            "state": "online",
                            "removable": False,
                            "block": "0",
                        }
                    ],
                    "block_devices": [
                        {
                            "name": "sda",
                            "type": "disk",
                            "size": f"{disk_gb}G",
                            "model": "Test Disk",
                        }
                    ],
                    "pci_devices": [],
                    "usb_devices": [],
                },
            },
            "metrics": {},
            "errors": [],
        }
        scan = Scan.objects.create(host=host, data=scan_data)
        Scan.objects.filter(pk=scan.pk).update(created_at=time)
        host.last_scan_cache = scan_data
        host.last_scan_date = time
        host.save()
