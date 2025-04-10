from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError

from hosts.models import Host, ScanData
from humitifier_common.artefacts import Hardware


@dataclass
class Costs:
    memory: float
    cpu: float
    storage: float
    linux: float
    windows: float


COSTS_2015 = Costs(
    memory=0.50,
    cpu=3.50,
    storage=10.50,
    linux=3.46,
    windows=26.03,
)

COSTS_2015v2 = Costs(
    memory=0.50,
    cpu=4.50,
    storage=10.50,
    linux=3.46,
    windows=26.03,
)

COSTS_2026 = Costs(
    memory=2.50,
    cpu=5,
    storage=10.00,
    linux=5.0,
    windows=40.00,
)

COSTS_2026v2 = Costs(
    memory=2.50,
    cpu=10,
    storage=10.00,
    linux=5.0,
    windows=40.00,
)

# CURRENT_COSTS = COSTS_2015
# CURRENT_COSTS = COSTS_2026
CURRENT_COSTS = COSTS_2015v2
# CURRENT_COSTS = COSTS_2026v2


class Command(BaseCommand):

    def handle(self, *args, **options):
        hosts = Host.objects.all()

        latest_scans: list[ScanData] = []

        for host in hosts:
            scan_obj: ScanData = host.get_scan_object()
            if not scan_obj.version >= 2:
                continue

            if Hardware.__artefact_name__ not in scan_obj.parsed_data.facts:
                continue

            if scan_obj.parsed_data.facts[Hardware.__artefact_name__] is None:
                continue

            latest_scans.append(scan_obj)

        for scan in latest_scans:
            hardware_info: Hardware = scan.parsed_data.facts[Hardware.__artefact_name__]

            total_memory = sum([memrange.size for memrange in hardware_info.memory])
            total_memory = total_memory / 1024 / 1024 / 1024

            disks = []
            for block_device in hardware_info.block_devices:
                if block_device.type == "disk":
                    disks.append(block_device)

            total_disk_space = 0
            for disk in disks:
                size = disk.size[:-1]
                unit = disk.size[-1]

                try:
                    size = int(size)
                except ValueError:
                    continue

                if unit == "M":
                    size = size / 1024
                    unit = "G"

                if unit == "G":
                    # We need to be in TB
                    size = size / 1024
                    unit = "T"

                total_disk_space += size

            print(scan.parsed_data.hostname)
            print(
                "CPUs",
                f"{hardware_info.num_cpus};",
                "Memory",
                f"{total_memory}GB;",
                "Disk Space",
                f"{round(total_disk_space, 2)}TB",
            )

            cost = CURRENT_COSTS.linux

            print(f"os ({cost} * 1)\t\t\t= ", cost)

            cpu_cost = CURRENT_COSTS.cpu * hardware_info.num_cpus
            cost += cpu_cost
            print(
                f"+ cpu ({CURRENT_COSTS.cpu} * "
                f"{hardware_info.num_cpus} = {cpu_cost})\t\t= {cost}"
            )

            mem_cost = CURRENT_COSTS.memory * total_memory  # TODO: check
            cost += mem_cost
            print(
                f"+ memory ({CURRENT_COSTS.memory} * {total_memory}) = {mem_cost})\t="
                f" {cost}"
            )

            storage_cost = CURRENT_COSTS.storage * total_disk_space
            cost += storage_cost

            print(
                f"+ storage ({CURRENT_COSTS.storage}"
                f" * {round(total_disk_space, 2)} = {round(storage_cost, 2)}) \t="
                f" {round(cost, 2)}"
            )

            # backup_cost = CURRENT_COSTS.storage * total_disk_space
            # cost += backup_cost
            #
            # print(
            #     f"+ backup ({CURRENT_COSTS.storage}"
            #     f" * {round(total_disk_space, 2)} = {round(backup_cost, 2)}) \t="
            #     f" {round(cost, 2)}"
            # )

            cost = round(cost, 2)
            print("TOTAL", cost)
            print()

            eligible_free_mem = hardware_info.num_cpus * 2
            paid_mem = max(0, total_memory - (2 * hardware_info.num_cpus))
            free_mem = total_memory - paid_mem
            free_mem_discount = free_mem * CURRENT_COSTS.memory
            cost -= free_mem_discount
            print(f"Total eligible free memory: {eligible_free_mem}GB")
            print(f"Actual free memory: {free_mem}GB")
            print(f"Free memory discount: {free_mem_discount}")
            print(f"NEW TOTAL: {round(cost,2)}")
            print("-" * 80)
