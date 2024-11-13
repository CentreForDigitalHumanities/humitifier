from django.core.management.base import BaseCommand, CommandError
from faker import Faker

from hosts.models import Host


class Command(BaseCommand):

    def handle(self, *args, **options):
        hosts = Host.objects.all()

        faker = Faker()

        for host in hosts:
            scan = host.scans.first()
            for i in range(1000):
                host.pk = None

                host.fqdn = faker.domain_name()

                host.save()

                scan.host = host

                for j in range(1000):
                    scan.pk = None
                    scan.save()
