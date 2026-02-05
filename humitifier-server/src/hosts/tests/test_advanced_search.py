"""Test cases for the advanced search feature."""

from datetime import datetime
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from hosts.models import Host, Scan
from hosts.search.query_builder import search_hosts_by_scan_fields
from hosts.search.query_parser import parse_query
from hosts.search.types import ComplexQuery, SearchCriterion


class AdvancedSearchTestCase(TestCase):
    """Base test case with helper methods for creating test data."""

    def setUp(self):
        """Set up test data with diverse hosts following proper artefact data structures."""
        self.now = timezone.now()

        # Host 1: Ubuntu web server with Apache
        self.host1 = Host.objects.create(
            fqdn="web01.example.com",
            department="Engineering",
            customer="internal",
            contact="devops@example.com",
            archived=False,
            billable=True,
        )
        self._create_scan(
            self.host1,
            {
                "version": 2,
                "scan_date": self.now.isoformat(),
                "hostname": "web01.example.com",
                "original_input": {
                    "hostname": "web01.example.com",
                    "artefacts": {},
                },
                "facts": {
                    "generic.HostnameCtl": {
                        "hostname": "web01",
                        "os": "Ubuntu 22.04.3 LTS",
                        "cpe_os_name": "cpe:/o:canonical:ubuntu_linux:22.04",
                        "kernel": "Linux 5.15.0-89-generic",
                        "virtualization": "kvm",
                    },
                    "generic.Hardware": {
                        "num_cpus": 8,
                        "memory": [
                            {
                                "range": "0x0000000000000000-0x000000007fffffff",
                                "size": 2147483648,
                                "state": "online",
                                "removable": False,
                                "block": "0",
                            },
                            {
                                "range": "0x0000000100000000-0x000000017fffffff",
                                "size": 2147483648,
                                "state": "online",
                                "removable": False,
                                "block": "1",
                            },
                        ],
                        "block_devices": [
                            {
                                "name": "sda",
                                "type": "disk",
                                "size": "500GB",
                                "model": "SAMSUNG SSD",
                            }
                        ],
                        "pci_devices": ["eth0", "vga0"],
                        "usb_devices": [],
                        "total_memory_gb": 16,
                    },
                    "generic.Users": [
                        {
                            "name": "root",
                            "uid": 0,
                            "gid": 0,
                            "info": "root",
                            "home": "/root",
                            "shell": "/bin/bash",
                        },
                        {
                            "name": "www-data",
                            "uid": 33,
                            "gid": 33,
                            "info": "www-data",
                            "home": "/var/www",
                            "shell": "/usr/sbin/nologin",
                        },
                    ],
                    "generic.Groups": [
                        {"name": "root", "gid": 0, "users": ["root"]},
                        {"name": "www-data", "gid": 33, "users": ["www-data"]},
                        {"name": "sudo", "gid": 27, "users": ["root", "admin"]},
                    ],
                    "generic.PackageList": [
                        {"name": "apache2", "version": "2.4.52-1ubuntu4.7"},
                        {"name": "php8.1", "version": "8.1.2-1ubuntu2.14"},
                        {"name": "mysql-server", "version": "8.0.35-0ubuntu0.22.04.1"},
                        {"name": "openssh-server", "version": "1:8.9p1-3ubuntu0.4"},
                        {"name": "vim", "version": "2:8.2.3995-1ubuntu2.12"},
                    ],
                    "generic.NetworkInterfaces": [
                        {
                            "name": "eth0",
                            "altnames": [],
                            "link_type": "ether",
                            "mac_address": "52:54:00:12:34:56",
                            "flags": ["UP", "BROADCAST", "RUNNING", "MULTICAST"],
                            "addresses": [
                                {
                                    "family": "inet",
                                    "address": "10.0.1.100",
                                    "scope": "global",
                                }
                            ],
                        },
                        {
                            "name": "lo",
                            "altnames": [],
                            "link_type": "loopback",
                            "mac_address": "00:00:00:00:00:00",
                            "flags": ["UP", "LOOPBACK", "RUNNING"],
                            "addresses": [
                                {
                                    "family": "inet",
                                    "address": "127.0.0.1",
                                    "scope": "host",
                                }
                            ],
                        },
                    ],
                    "generic.SELinux": {
                        "enabled": False,
                        "policy_name": None,
                        "mode": None,
                    },
                    "server.Webserver": {
                        "hosts": [
                            {
                                "listen_ports": [80, 443],
                                "webserver": "apache",
                                "filename": "/etc/apache2/sites-enabled/example.conf",
                                "document_root": "/var/www/html",
                                "hostname": "example.com",
                                "hostname_aliases": ["www.example.com"],
                                "locations": {},
                                "rewrite_rules": [],
                                "includes": [],
                            }
                        ]
                    },
                    "server.PuppetAgent": {
                        "enabled": True,
                        "running": True,
                        "disabled_message": None,
                        "code_roles": ["webserver", "php"],
                        "profiles": ["apache", "mysql"],
                        "environment": "production",
                        "data_role": "web",
                        "data_role_variant": "apache",
                        "last_run": "2024-01-15T10:30:00Z",
                        "is_failing": False,
                    },
                },
                "metrics": {
                    "generic.Memory": {
                        "total_mb": 16384,
                        "used_mb": 8192,
                        "free_mb": 8192,
                        "swap_total_mb": 2048,
                        "swap_used_mb": 0,
                        "swap_free_mb": 2048,
                    },
                    "generic.Blocks": [
                        {
                            "name": "/dev/sda1",
                            "size_mb": 476940,
                            "used_mb": 238470,
                            "available_mb": 238470,
                            "use_percent": 50,
                            "mount": "/",
                        }
                    ],
                    "server.Uptime": 2592000.5,
                },
                "errors": [],
            },
        )

        # Host 2: Debian database server
        self.host2 = Host.objects.create(
            fqdn="db01.example.com",
            department="Engineering",
            customer="internal",
            contact="dba@example.com",
            archived=False,
            billable=True,
        )
        self._create_scan(
            self.host2,
            {
                "version": 2,
                "scan_date": self.now.isoformat(),
                "hostname": "db01.example.com",
                "original_input": {
                    "hostname": "db01.example.com",
                    "artefacts": {},
                },
                "facts": {
                    "generic.HostnameCtl": {
                        "hostname": "db01",
                        "os": "Debian GNU/Linux 12 (bookworm)",
                        "cpe_os_name": "cpe:/o:debian:debian_linux:12",
                        "kernel": "Linux 6.1.0-13-amd64",
                        "virtualization": "kvm",
                    },
                    "generic.Hardware": {
                        "num_cpus": 16,
                        "memory": [
                            {
                                "range": "0x0000000000000000-0x00000000ffffffff",
                                "size": 4294967296,
                                "state": "online",
                                "removable": False,
                                "block": "0",
                            },
                        ],
                        "block_devices": [
                            {
                                "name": "sda",
                                "type": "disk",
                                "size": "1TB",
                                "model": "WD Red",
                            },
                            {
                                "name": "sdb",
                                "type": "disk",
                                "size": "1TB",
                                "model": "WD Red",
                            },
                        ],
                        "pci_devices": ["eth0", "eth1"],
                        "usb_devices": [],
                        "total_memory_gb": 32,
                    },
                    "generic.Users": [
                        {
                            "name": "root",
                            "uid": 0,
                            "gid": 0,
                            "info": "root",
                            "home": "/root",
                            "shell": "/bin/bash",
                        },
                        {
                            "name": "postgres",
                            "uid": 999,
                            "gid": 999,
                            "info": "PostgreSQL administrator",
                            "home": "/var/lib/postgresql",
                            "shell": "/bin/bash",
                        },
                        {
                            "name": "mysql",
                            "uid": 998,
                            "gid": 998,
                            "info": "MySQL Server",
                            "home": "/nonexistent",
                            "shell": "/bin/false",
                        },
                    ],
                    "generic.Groups": [
                        {"name": "root", "gid": 0, "users": ["root"]},
                        {"name": "postgres", "gid": 999, "users": ["postgres"]},
                        {"name": "mysql", "gid": 998, "users": ["mysql"]},
                        {"name": "sudo", "gid": 27, "users": ["root"]},
                    ],
                    "generic.PackageList": [
                        {"name": "postgresql-15", "version": "15.4-1.pgdg120+1"},
                        {"name": "mysql-server", "version": "8.0.34-1debian12"},
                        {"name": "openssh-server", "version": "1:9.2p1-2"},
                        {"name": "vim", "version": "2:9.0.1378-2"},
                        {"name": "htop", "version": "3.2.2-1"},
                    ],
                    "generic.NetworkInterfaces": [
                        {
                            "name": "eth0",
                            "altnames": [],
                            "link_type": "ether",
                            "mac_address": "52:54:00:ab:cd:ef",
                            "flags": ["UP", "BROADCAST", "RUNNING", "MULTICAST"],
                            "addresses": [
                                {
                                    "family": "inet",
                                    "address": "10.0.1.200",
                                    "scope": "global",
                                }
                            ],
                        },
                    ],
                    "generic.SELinux": {
                        "enabled": False,
                        "policy_name": None,
                        "mode": None,
                    },
                    "server.PuppetAgent": {
                        "enabled": True,
                        "running": True,
                        "disabled_message": None,
                        "code_roles": ["database"],
                        "profiles": ["postgresql", "mysql"],
                        "environment": "production",
                        "data_role": "database",
                        "data_role_variant": "postgresql",
                        "last_run": "2024-01-15T10:35:00Z",
                        "is_failing": False,
                    },
                },
                "metrics": {
                    "generic.Memory": {
                        "total_mb": 32768,
                        "used_mb": 24576,
                        "free_mb": 8192,
                        "swap_total_mb": 4096,
                        "swap_used_mb": 512,
                        "swap_free_mb": 3584,
                    },
                    "generic.Blocks": [
                        {
                            "name": "/dev/sda1",
                            "size_mb": 953868,
                            "used_mb": 762000,
                            "available_mb": 191868,
                            "use_percent": 80,
                            "mount": "/",
                        },
                        {
                            "name": "/dev/sdb1",
                            "size_mb": 953868,
                            "used_mb": 476934,
                            "available_mb": 476934,
                            "use_percent": 50,
                            "mount": "/var/lib/postgresql",
                        },
                    ],
                    "server.Uptime": 7776000.0,
                },
                "errors": [],
            },
        )

        # Host 3: CentOS archived host
        self.host3 = Host.objects.create(
            fqdn="legacy01.example.com",
            department="IT",
            customer="internal",
            contact="it@example.com",
            archived=True,
            billable=False,
        )
        self._create_scan(
            self.host3,
            {
                "version": 2,
                "scan_date": self.now.isoformat(),
                "hostname": "legacy01.example.com",
                "original_input": {
                    "hostname": "legacy01.example.com",
                    "artefacts": {},
                },
                "facts": {
                    "generic.HostnameCtl": {
                        "hostname": "legacy01",
                        "os": "CentOS Linux 7 (Core)",
                        "cpe_os_name": "cpe:/o:centos:centos:7",
                        "kernel": "Linux 3.10.0-1160.el7.x86_64",
                        "virtualization": "vmware",
                    },
                    "generic.Hardware": {
                        "num_cpus": 4,
                        "memory": [
                            {
                                "range": "0x0000000000000000-0x000000003fffffff",
                                "size": 1073741824,
                                "state": "online",
                                "removable": False,
                                "block": "0",
                            },
                        ],
                        "block_devices": [
                            {
                                "name": "sda",
                                "type": "disk",
                                "size": "100GB",
                                "model": "VMware Virtual",
                            }
                        ],
                        "pci_devices": ["eth0"],
                        "usb_devices": [],
                        "total_memory_gb": 8,
                    },
                    "generic.Users": [
                        {
                            "name": "root",
                            "uid": 0,
                            "gid": 0,
                            "info": "root",
                            "home": "/root",
                            "shell": "/bin/bash",
                        },
                    ],
                    "generic.Groups": [
                        {"name": "root", "gid": 0, "users": ["root"]},
                    ],
                    "generic.PackageList": [
                        {"name": "httpd", "version": "2.4.6-97.el7.centos.5"},
                        {"name": "openssh-server", "version": "7.4p1-22.el7_9"},
                    ],
                    "generic.NetworkInterfaces": [
                        {
                            "name": "eth0",
                            "altnames": [],
                            "link_type": "ether",
                            "mac_address": "00:50:56:12:34:56",
                            "flags": ["UP", "BROADCAST", "RUNNING", "MULTICAST"],
                            "addresses": [
                                {
                                    "family": "inet",
                                    "address": "192.168.1.50",
                                    "scope": "global",
                                }
                            ],
                        },
                    ],
                    "generic.SELinux": {
                        "enabled": True,
                        "policy_name": "targeted",
                        "mode": "enforcing",
                    },
                    "server.PuppetAgent": {
                        "enabled": False,
                        "running": False,
                        "disabled_message": "Host decommissioned",
                        "code_roles": None,
                        "profiles": None,
                        "environment": None,
                        "data_role": None,
                        "data_role_variant": None,
                        "last_run": None,
                        "is_failing": None,
                    },
                },
                "metrics": {
                    "generic.Memory": {
                        "total_mb": 8192,
                        "used_mb": 2048,
                        "free_mb": 6144,
                        "swap_total_mb": 1024,
                        "swap_used_mb": 0,
                        "swap_free_mb": 1024,
                    },
                    "generic.Blocks": [
                        {
                            "name": "/dev/sda1",
                            "size_mb": 95367,
                            "used_mb": 19073,
                            "available_mb": 76294,
                            "use_percent": 20,
                            "mount": "/",
                        }
                    ],
                    "server.Uptime": 864000.0,
                },
                "errors": [],
            },
        )

        # Host 4: Ubuntu with ZFS storage
        self.host4 = Host.objects.create(
            fqdn="storage01.example.com",
            department="Engineering",
            customer="acme-corp",
            contact="storage@example.com",
            archived=False,
            billable=True,
        )
        self._create_scan(
            self.host4,
            {
                "version": 2,
                "scan_date": self.now.isoformat(),
                "hostname": "storage01.example.com",
                "original_input": {
                    "hostname": "storage01.example.com",
                    "artefacts": {},
                },
                "facts": {
                    "generic.HostnameCtl": {
                        "hostname": "storage01",
                        "os": "Ubuntu 22.04.3 LTS",
                        "cpe_os_name": "cpe:/o:canonical:ubuntu_linux:22.04",
                        "kernel": "Linux 5.15.0-89-generic",
                        "virtualization": "kvm",
                    },
                    "generic.Hardware": {
                        "num_cpus": 12,
                        "memory": [
                            {
                                "range": "0x0000000000000000-0x00000000bfffffff",
                                "size": 3221225472,
                                "state": "online",
                                "removable": False,
                                "block": "0",
                            },
                        ],
                        "block_devices": [
                            {
                                "name": "sda",
                                "type": "disk",
                                "size": "2TB",
                                "model": "HGST HDD",
                            },
                            {
                                "name": "sdb",
                                "type": "disk",
                                "size": "2TB",
                                "model": "HGST HDD",
                            },
                            {
                                "name": "sdc",
                                "type": "disk",
                                "size": "2TB",
                                "model": "HGST HDD",
                            },
                        ],
                        "pci_devices": ["eth0"],
                        "usb_devices": [],
                        "total_memory_gb": 64,
                    },
                    "generic.Users": [
                        {
                            "name": "root",
                            "uid": 0,
                            "gid": 0,
                            "info": "root",
                            "home": "/root",
                            "shell": "/bin/bash",
                        },
                    ],
                    "generic.Groups": [
                        {"name": "root", "gid": 0, "users": ["root"]},
                    ],
                    "generic.PackageList": [
                        {"name": "zfsutils-linux", "version": "2.1.5-1ubuntu6~22.04.2"},
                        {"name": "openssh-server", "version": "1:8.9p1-3ubuntu0.4"},
                        {"name": "nfs-kernel-server", "version": "1:2.6.1-1ubuntu1.2"},
                    ],
                    "generic.NetworkInterfaces": [
                        {
                            "name": "eth0",
                            "altnames": [],
                            "link_type": "ether",
                            "mac_address": "52:54:00:99:88:77",
                            "flags": ["UP", "BROADCAST", "RUNNING", "MULTICAST"],
                            "addresses": [
                                {
                                    "family": "inet",
                                    "address": "10.0.2.100",
                                    "scope": "global",
                                }
                            ],
                        },
                    ],
                    "generic.SELinux": {
                        "enabled": False,
                        "policy_name": None,
                        "mode": None,
                    },
                    "server.PuppetAgent": {
                        "enabled": True,
                        "running": True,
                        "disabled_message": None,
                        "code_roles": ["storage", "nfs"],
                        "profiles": ["zfs"],
                        "environment": "production",
                        "data_role": "storage",
                        "data_role_variant": "zfs",
                        "last_run": "2024-01-15T10:40:00Z",
                        "is_failing": False,
                    },
                },
                "metrics": {
                    "generic.Memory": {
                        "total_mb": 65536,
                        "used_mb": 16384,
                        "free_mb": 49152,
                        "swap_total_mb": 8192,
                        "swap_used_mb": 0,
                        "swap_free_mb": 8192,
                    },
                    "generic.Blocks": [
                        {
                            "name": "/dev/sda1",
                            "size_mb": 100000,
                            "used_mb": 20000,
                            "available_mb": 80000,
                            "use_percent": 20,
                            "mount": "/",
                        }
                    ],
                    "special.ZFS": {
                        "pools": [
                            {"name": "tank", "size_mb": 6000000, "used_mb": 3000000}
                        ],
                        "volumes": [
                            {
                                "name": "tank/data",
                                "size_mb": 5000000,
                                "used_mb": 2500000,
                                "mount": "/tank/data",
                            }
                        ],
                    },
                    "server.Uptime": 5184000.0,
                },
                "errors": [],
            },
        )

    def _create_scan(self, host: Host, data: dict):
        """Helper to create a scan with given data."""
        with mock.patch("django.utils.timezone.now", mock.Mock(return_value=self.now)):
            Scan.objects.create(host=host, data=data)
            host.last_scan_cache = data
            host.save()


class SimpleSearchTests(AdvancedSearchTestCase):
    """Test cases for simple search queries."""

    def test_search_by_meta_fqdn(self):
        """Test searching by FQDN using meta field."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="meta.fqdn", operator="contains", value="web"
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().fqdn, "web01.example.com")

    def test_search_by_meta_department(self):
        """Test searching by department."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="meta.department", operator="eq", value="Engineering"
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 3)

    def test_search_by_meta_archived(self):
        """Test searching by archived status."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="meta.archived", operator="eq", value=True
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().fqdn, "legacy01.example.com")

    def test_search_by_meta_billable(self):
        """Test searching by billable status."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="meta.billable", operator="eq", value=False
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().fqdn, "legacy01.example.com")

    def test_search_by_os_string(self):
        """Test searching by OS using string contains."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="facts.generic.HostnameCtl.os",
                operator="contains",
                value="Ubuntu",
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 2)

    def test_search_by_cpu_count_exact(self):
        """Test searching by CPU count with exact match."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="facts.generic.Hardware.num_cpus", operator="eq", value=8
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().fqdn, "web01.example.com")

    def test_search_by_cpu_count_gte(self):
        """Test searching by CPU count with greater than or equal."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="facts.generic.Hardware.num_cpus", operator="gte", value=12
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 2)
        fqdns = {host.fqdn for host in result}
        self.assertIn("db01.example.com", fqdns)
        self.assertIn("storage01.example.com", fqdns)

    def test_search_by_cpu_count_lt(self):
        """Test searching by CPU count with less than."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="facts.generic.Hardware.num_cpus", operator="lt", value=8
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().fqdn, "legacy01.example.com")

    def test_search_by_memory_total(self):
        """Test searching by total memory."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="facts.generic.Hardware.total_memory_gb",
                operator="gte",
                value=32,
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 2)
        fqdns = {host.fqdn for host in result}
        self.assertIn("db01.example.com", fqdns)
        self.assertIn("storage01.example.com", fqdns)

    def test_search_by_virtualization(self):
        """Test searching by virtualization type."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="facts.generic.HostnameCtl.virtualization",
                operator="eq",
                value="vmware",
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().fqdn, "legacy01.example.com")

    def test_search_by_selinux_enabled(self):
        """Test searching by SELinux enabled status."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="facts.generic.SELinux.enabled", operator="eq", value=True
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().fqdn, "legacy01.example.com")

    def test_search_by_puppet_enabled(self):
        """Test searching by Puppet enabled status."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="facts.server.PuppetAgent.enabled", operator="eq", value=True
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 3)

    def test_search_by_puppet_environment(self):
        """Test searching by Puppet environment."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="facts.server.PuppetAgent.environment",
                operator="eq",
                value="production",
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 3)

    def test_search_by_memory_metric_used(self):
        """Test searching by used memory metric."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="metrics.generic.Memory.used_mb", operator="gte", value=20000
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().fqdn, "db01.example.com")

    def test_search_no_results(self):
        """Test search that should return no results."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="facts.generic.Hardware.num_cpus", operator="eq", value=999
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 0)

    def test_search_with_customer(self):
        """Test searching by customer."""
        query = ComplexQuery(
            type="criterion",
            criterion=SearchCriterion(
                field_id="meta.customer", operator="eq", value="acme-corp"
            ),
        )
        result = search_hosts_by_scan_fields(Host.objects.all(), query)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().fqdn, "storage01.example.com")


class ComplexSearchTests(AdvancedSearchTestCase):
    """Test cases for complex search queries using the query parser."""

    def test_and_query_with_parser(self):
        """Test AND query using query parser."""
        query_string = (
            'meta.department = "Engineering" AND facts.generic.Hardware.num_cpus >= 8'
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 3)

    def test_or_query_with_parser(self):
        """Test OR query using query parser."""
        query_string = (
            'facts.generic.HostnameCtl.os contains "Ubuntu" OR '
            'facts.generic.HostnameCtl.os contains "Debian"'
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 3)

    def test_nested_and_or_query(self):
        """Test nested AND/OR query."""
        query_string = (
            '{facts.generic.HostnameCtl.os contains "Ubuntu" OR '
            'facts.generic.HostnameCtl.os contains "Debian"} AND '
            "facts.generic.Hardware.num_cpus >= 8"
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 3)

    def test_complex_nested_query(self):
        """Test complex nested query with multiple conditions."""
        query_string = (
            '{meta.department = "Engineering" AND facts.generic.Hardware.num_cpus >= 12} OR '
            "{meta.archived = true AND facts.generic.Hardware.num_cpus < 8}"
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 3)
        fqdns = {host.fqdn for host in result}
        self.assertIn("db01.example.com", fqdns)
        self.assertIn("storage01.example.com", fqdns)
        self.assertIn("legacy01.example.com", fqdns)

    def test_multiple_and_conditions(self):
        """Test multiple AND conditions."""
        query_string = (
            'meta.department = "Engineering" AND '
            "facts.generic.Hardware.num_cpus >= 8 AND "
            'facts.generic.HostnameCtl.virtualization = "kvm"'
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 3)

    def test_search_with_boolean_and_string(self):
        """Test combining boolean and string searches."""
        query_string = (
            'meta.archived = false AND facts.generic.HostnameCtl.os contains "Ubuntu"'
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 2)
        fqdns = {host.fqdn for host in result}
        self.assertIn("web01.example.com", fqdns)
        self.assertIn("storage01.example.com", fqdns)

    def test_search_with_multiple_numeric_conditions(self):
        """Test multiple numeric comparisons."""
        query_string = (
            "facts.generic.Hardware.num_cpus >= 8 AND "
            "facts.generic.Hardware.num_cpus <= 16"
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 3)

    def test_complex_or_with_different_fields(self):
        """Test OR query with different field types."""
        query_string = (
            'meta.department = "IT" OR ' "facts.generic.Hardware.total_memory_gb >= 32"
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 3)

    def test_deep_nesting_with_brackets(self):
        """Test deeply nested query with multiple brackets."""
        query_string = (
            "{{facts.generic.Hardware.num_cpus >= 12 OR "
            "facts.generic.Hardware.total_memory_gb >= 64} AND "
            "meta.archived = false} OR "
            '{meta.department = "IT" AND facts.generic.Hardware.num_cpus < 8}'
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 3)

    def test_search_puppet_and_webserver(self):
        """Test searching for hosts with Puppet enabled and running webserver."""
        query_string = (
            "facts.server.PuppetAgent.enabled = true AND "
            "facts.server.PuppetAgent.is_failing = false"
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 3)

    def test_search_by_metrics_with_and(self):
        """Test searching by multiple metrics."""
        query_string = (
            "metrics.generic.Memory.total_mb >= 16384 AND "
            "metrics.generic.Memory.free_mb >= 8192"
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 3)


class ArrayFieldSearchTests(AdvancedSearchTestCase):
    """Test cases for searching array fields."""

    def test_count_users(self):
        """Test counting users using array aggregation."""
        query_string = "count(facts.generic.Users[].name) >= 2"
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 2)
        fqdns = {host.fqdn for host in result}
        self.assertIn("web01.example.com", fqdns)
        self.assertIn("db01.example.com", fqdns)

    def test_count_groups(self):
        """Test counting groups."""
        query_string = "count(facts.generic.Groups[].name) >= 3"
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 2)

    def test_count_packages(self):
        """Test counting packages."""
        query_string = "count(facts.generic.PackageList[].name) >= 5"
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 2)

    def test_count_block_devices(self):
        """Test counting block devices."""
        query_string = "count(facts.generic.Hardware.block_devices[].name) >= 2"
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 2)
        fqdns = {host.fqdn for host in result}
        self.assertIn("db01.example.com", fqdns)
        self.assertIn("storage01.example.com", fqdns)

    def test_max_memory_size(self):
        """Test maximum memory block size."""
        query_string = "max(facts.generic.Hardware.memory[].size) >= 4000000000"
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().fqdn, "db01.example.com")

    def test_count_network_interfaces(self):
        """Test counting network interfaces."""
        query_string = "count(facts.generic.NetworkInterfaces[].name) >= 2"
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().fqdn, "web01.example.com")

    def test_filter_packages_by_pattern(self):
        """Test filtering packages by pattern."""
        query_string = (
            'filter(facts.generic.PackageList[].name, "apache") contains "apache2"'
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().fqdn, "web01.example.com")

    def test_count_filtered_packages(self):
        """Test counting filtered packages."""
        query_string = 'count(filter(facts.generic.PackageList[].name, "ssh")) > 0'
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        # All hosts should have openssh-server
        self.assertEqual(result.count(), 4)

    def test_array_search_with_other_conditions(self):
        """Test combining array search with other conditions."""
        query_string = (
            "count(facts.generic.Users[].name) >= 2 AND "
            'meta.department = "Engineering"'
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 2)


class EdgeCaseTests(AdvancedSearchTestCase):
    """Test edge cases and error conditions."""

    def test_empty_query(self):
        """Test empty query returns all hosts."""
        result = search_hosts_by_scan_fields(Host.objects.all(), None)
        self.assertEqual(result.count(), 4)

    def test_search_null_field(self):
        """Test searching for null values."""
        query_string = (
            'facts.server.PuppetAgent.disabled_message contains "decommission"'
        )
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().fqdn, "legacy01.example.com")

    def test_search_with_special_characters(self):
        """Test searching with special characters in strings."""
        query_string = 'facts.generic.HostnameCtl.kernel contains "5.15.0-89"'
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 2)

    def test_case_insensitive_contains(self):
        """Test case-insensitive contains search."""
        query_string = 'facts.generic.HostnameCtl.os contains "ubuntu"'
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 2)

    def test_search_with_zero_value(self):
        """Test searching for zero values."""
        query_string = "metrics.generic.Memory.swap_used_mb = 0"
        parsed_query = parse_query(query_string)
        result = search_hosts_by_scan_fields(Host.objects.all(), parsed_query)
        self.assertEqual(result.count(), 3)

    def test_invalid_field_id(self):
        """Test that invalid field IDs raise ValueError."""
        with self.assertRaises(ValueError):
            parse_query("invalid.field.id = 123")

    def test_malformed_query(self):
        """Test that malformed queries raise ValueError."""
        with self.assertRaises(ValueError):
            parse_query("meta.fqdn = ")
