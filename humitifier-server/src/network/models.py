from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from ipaddress import ip_network

from django.core.exceptions import ValidationError
from django.db import models

from humitifier_common.index_data import IndexedIP


def _validate_cidr_range(value):
    if not value:
        raise ValidationError("CIDR range cannot be empty")

    if "/" not in value:
        raise ValidationError("CIDR range must be in the format 'x.x.x.x/x'")

    try:
        ip_network(value)
    except ValueError:
        raise ValidationError("Invalid CIDR range")


class Network(models.Model):
    name = models.CharField(max_length=100)
    vlan = models.IntegerField()
    cidr_range = models.CharField(max_length=100, validators=[_validate_cidr_range])

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_cidr = None
        if not is_new:
            old_cidr = Network.objects.get(pk=self.pk).cidr_range

        super().save(*args, **kwargs)

        if is_new or old_cidr != self.cidr_range:
            self.update_ip_infos()

    def update_ip_infos(self):
        network = list(ip_network(self.cidr_range))[1:]
        existing_ips = {ip.ip_address: ip for ip in self.ipinfo_set.all()}

        new_ips = []
        all_ip_strs = set()
        for ip in network:
            ip_str = str(ip)
            all_ip_strs.add(ip_str)
            if ip_str not in existing_ips:
                new_ips.append(IPInfo(network=self, ip_address=ip_str))

        if new_ips:
            IPInfo.objects.bulk_create(new_ips)

        ips_to_delete = [
            ip_addr for ip_addr in existing_ips.keys() if ip_addr not in all_ip_strs
        ]
        if ips_to_delete:
            self.ipinfo_set.filter(ip_address__in=ips_to_delete).delete()

    def __str__(self):
        return f"{self.cidr_range} ({self.name})"


class IPInfo(models.Model):
    network = models.ForeignKey(Network, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()

    active = models.BooleanField(default=False)
    ping_time = models.FloatField(null=True, blank=True)
    reverse_dns_entries = ArrayField(
        models.CharField(max_length=255), blank=True, null=True
    )
    port_status = models.JSONField(null=True, blank=True)

    hosts_from_ip = models.ManyToManyField("hosts.Host", related_name="ipinfo_from_ip")
    hosts_from_dns = models.ManyToManyField(
        "hosts.Host", related_name="ipinfo_from_dns"
    )

    last_indexed = models.DateTimeField(null=True, blank=True)
    last_index_scheduled = models.DateTimeField(null=True, blank=True)

    def update_from_indexed_ip(self, indexed_ip: IndexedIP):
        self.active = indexed_ip.active
        self.ping_time = indexed_ip.ping_time
        self.reverse_dns_entries = indexed_ip.reverse_dns
        self.port_status = indexed_ip.ports
        self.last_indexed = timezone.now()
        self.save()

    def get_ping_time_display(self):
        if self.ping_time is None:
            return ""
        return f"{self.ping_time:.2f} ms"

    def get_reverse_dns_entries_display(self):
        if not self.reverse_dns_entries:
            return ""
        return ", ".join(self.reverse_dns_entries)
