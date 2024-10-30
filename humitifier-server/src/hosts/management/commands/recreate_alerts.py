from django.core.management.base import BaseCommand

from hosts.alerts import generate_alerts
from hosts.models import Host


class Command(BaseCommand):

    def handle(self, *args, **options):
        hosts = Host.objects.all()

        for host in hosts:
            generate_alerts(host.last_scan_cache, host)