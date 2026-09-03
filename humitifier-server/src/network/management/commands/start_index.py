from django.core.management import BaseCommand

from network.models import IPInfo
from network.utils import start_index


class Command(BaseCommand):
    help = "Starts the network indexer"

    def add_arguments(self, parser):
        parser.add_argument("ip_address", type=str, help="IP address to index")

    def handle(self, *args, **options):
        ip = IPInfo.objects.get(ip_address=options["ip_address"])

        start_index(ip, ports=[22, 80, 443, 7000, 8000, 8080, 8443, 5432, 3306])
