from django.core.management.base import BaseCommand, CommandError

from hosts.models import Host, ScanScheduling


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("host")

    def handle(self, *args, **options):
        from hosts.tasks import start_scan

        host = Host.objects.get(fqdn=options["host"])

        if (
            host.data_source
            and host.data_source.scan_scheduling != ScanScheduling.SCHEDULED
        ):
            raise CommandError(
                "Cannot queue scans for hosts using non-scheduled scheduling"
            )

        start_scan.delay(host.fqdn)
