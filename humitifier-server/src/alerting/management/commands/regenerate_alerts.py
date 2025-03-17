from django.core.management.base import BaseCommand, CommandError

from alerting.utils import regenerate_alerts
from hosts.models import Host


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--host")
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, **options):

        if options["all"]:
            hosts = Host.objects.all()
        else:
            hosts = Host.objects.filter(fqdn=options["host"])

        if not hosts:
            raise CommandError("No hosts found")

        for host in hosts:
            task = regenerate_alerts(host)

            print("Queued task: {}".format(task))
