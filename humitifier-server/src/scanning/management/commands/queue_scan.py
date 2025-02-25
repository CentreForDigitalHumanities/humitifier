from django.core.management.base import BaseCommand, CommandError

from hosts.models import Host
from humitifier_server import settings


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--host")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, **options):
        from scanning.tasks import start_scan

        if options["all"]:
            hosts = Host.objects.all()
        else:
            hosts = Host.objects.filter(fqdn=options["host"])

        for host in hosts:
            if not host.can_schedule_scan:
                if not settings.DEBUG and not options["force"]:
                    print(
                        host.fqdn,
                        "Cannot queue scans for hosts using non-scheduled scheduling",
                    )

            start_scan.delay(host.fqdn)
