from pydantic import BaseModel

from humitifier_common.artefacts.groups import WINDOWS_GENERIC
from humitifier_common.artefacts.registry import fact


class WindowsDisk(BaseModel):
    name: str
    health_status: str
    model_name: str
    bus_type: str
    serial_number: str | None
    size: int
    disk_number: int
    unique_id: str


class WindowsCPU(BaseModel):
    name: str
    manufacturer: str
    num_cores: int
    num_logical_cores: int
    socket: str


@fact(group=WINDOWS_GENERIC)
class WindowsHardware(BaseModel):
    disks: list[WindowsDisk]
    cpus: list[WindowsCPU]
    memory_size: int
