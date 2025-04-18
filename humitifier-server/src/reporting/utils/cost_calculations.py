from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from humitifier_common.artefacts import Hardware
from reporting.models import CostsScheme


@dataclass
class CostsBreakdown:
    # Costs
    cpu: Decimal
    memory: Decimal
    memory_correction: Decimal
    storage: Decimal
    redundant_storage: Decimal
    os: Decimal

    # Units
    num_cpu: int
    memory_size: Decimal
    bundled_memory_size: Decimal
    storage_size: Decimal
    redundant_storage_size: Decimal

    @property
    def gross_vm_costs(self):
        return self.cpu + self.memory + self.os

    @property
    def net_vm_costs(self):
        return self.gross_vm_costs - self.memory_correction

    @property
    def total_storage_usage(self):
        return self.storage_size + self.redundant_storage_size

    @property
    def total_storage_costs(self):
        return self.storage + self.redundant_storage

    @property
    def total_costs(self):
        return self.total_storage_costs + self.net_vm_costs


def calculate_costs(
    num_cpu: int,
    memory_in_gb: Decimal,
    storage_in_gb: Decimal,
    os: Literal["linux", "windows"],
    costs_scheme: CostsScheme,
    redundant_storage: bool = False,
    bundle_memory: bool = False,
    memory_in_bundle: int = 2,
) -> CostsBreakdown:

    # CPU
    cpu_costs = costs_scheme.cpu * num_cpu

    # Memory
    memory_costs = costs_scheme.memory * memory_in_gb
    if bundle_memory:
        max_bundled_memory = num_cpu * memory_in_bundle
        actual_bundled_memory = min(memory_in_gb, max_bundled_memory)
        bundled_memory_cost = actual_bundled_memory * costs_scheme.memory
    else:
        bundled_memory_cost = 0
        actual_bundled_memory = 0

    # Storage
    storage_costs = costs_scheme.storage_per_gb * storage_in_gb
    if redundant_storage:
        redundant_storage_costs = storage_costs
    else:
        redundant_storage_costs = 0

    # OS
    if os == "linux":
        os_cost = costs_scheme.linux
    elif os == "windows":
        os_cost = costs_scheme.windows
    else:
        os_cost = 0

    return CostsBreakdown(
        # Costs
        cpu=cpu_costs,
        memory=memory_costs,
        memory_correction=bundled_memory_cost,
        storage=storage_costs,
        redundant_storage=redundant_storage_costs,
        os=os_cost,
        # Units
        num_cpu=num_cpu,
        memory_size=memory_in_gb,
        bundled_memory_size=actual_bundled_memory,
        storage_size=storage_in_gb,
        redundant_storage_size=storage_in_gb if redundant_storage else 0,
    )


def calculate_from_hardware_artefact(
    hardware: Hardware,
    costs_scheme: CostsScheme,
    redundant_storage: bool = False,
    bundle_memory: bool = False,
    memory_in_bundle: int = 2,
) -> CostsBreakdown:

    # Memory
    total_memory = Decimal(sum([memrange.size for memrange in hardware.memory]))
    total_memory = total_memory / 1024 / 1024 / 1024

    # Storage
    disks = []
    for block_device in hardware.block_devices:
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

        if unit == "K":
            size = size / 1024
            unit = "M"

        if unit == "M":
            size = size / 1024
            unit = "G"

        if unit == "T":
            size = size * 1024
            unit = "G"

        total_disk_space += size

    return calculate_costs(
        num_cpu=hardware.num_cpus,
        memory_in_gb=total_memory,
        storage_in_gb=total_disk_space,
        os="linux",
        costs_scheme=costs_scheme,
        redundant_storage=redundant_storage,
        bundle_memory=bundle_memory,
        memory_in_bundle=memory_in_bundle,
    )
