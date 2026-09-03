from django.test import TestCase
from .models import Network, IPInfo

class NetworkModelTest(TestCase):
    def test_ip_info_creation_on_save(self):
        network = Network.objects.create(
            name="Test Network",
            vlan=10,
            cidr_range="192.168.1.0/29"
        )
        # 192.168.1.0/29 has 8 IPs
        self.assertEqual(network.ipinfo_set.count(), 8)

    def test_ip_info_update_on_range_change(self):
        network = Network.objects.create(
            name="Test Network",
            vlan=10,
            cidr_range="192.168.1.0/30"
        )
        # 192.168.1.0/30 has 4 IPs
        self.assertEqual(network.ipinfo_set.count(), 4)

        network.cidr_range = "192.168.1.0/29"
        network.save()
        self.assertEqual(network.ipinfo_set.count(), 8)

        network.cidr_range = "192.168.1.4/30"
        network.save()
        # Should delete old ones and create new ones (4-7)
        self.assertEqual(network.ipinfo_set.count(), 4)
        self.assertTrue(network.ipinfo_set.filter(ip_address="192.168.1.4").exists())
        self.assertFalse(network.ipinfo_set.filter(ip_address="192.168.1.0").exists())
