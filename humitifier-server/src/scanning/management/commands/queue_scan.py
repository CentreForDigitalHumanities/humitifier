from django.core.management.base import BaseCommand, CommandError

from hosts.models import Host
from humitifier_server import settings


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--host")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--delay")

    def handle(self, *args, **options):
        from scanning.utils.start_scan import start_full_scan

        if options["all"]:
            hosts = Host.objects.all()
        else:
            hosts = Host.objects.filter(fqdn=options["host"])

        if not hosts:
            raise CommandError("No hosts found")

        for host in hosts:
            if not host.can_schedule_scan:
                if not settings.DEBUG and not options["force"]:
                    print(
                        host.fqdn,
                        "Cannot queue scans for hosts using non-scheduled scheduling",
                    )

            delay = None
            if options["delay"]:
                try:
                    delay = int(options["delay"])
                    if delay < 0:
                        raise ValueError
                except ValueError:
                    raise CommandError(
                        "Invalid value for delay, please use a positive integer"
                    )

            task = start_full_scan(host, force=options["force"], delay_seconds=delay)

            print("Queued task: {}".format(task))
