import json
from pprint import pformat

from humitifier_common.artefacts import WindowsCPU
from humitifier_common.artefacts.windows import WindowsHardware, WindowsDisk
from humitifier_common.scan_data import ErrorTypeEnum, ScanErrorMetadata
from humitifier_scanner.collectors import CollectInfo, T
from humitifier_scanner.collectors.backend import WindowsShellCollector
from humitifier_scanner.executor.windows_shell import WindowsShellExecutor
from humitifier_scanner.logger import logger


class WindowsHardwareFactCollector(WindowsShellCollector):
    fact = WindowsHardware

    def collect_from_shell(
        self, shell_executor: WindowsShellExecutor, info: CollectInfo
    ) -> WindowsHardware:

        get_disks_cmd = shell_executor.execute_pwsh_json(
            "Get-Disk | Select-Object -Property FriendlyName, HealthStatus, Model, BusType, SerialNumber, Size, DiskNumber, UniqueId"
        )

        disks = []
        if get_disks_cmd.return_code == 0:
            for disk in get_disks_cmd.data:
                disks.append(
                    WindowsDisk(
                        name=disk["FriendlyName"],
                        health_status=disk["HealthStatus"],
                        model_name=disk["Model"],
                        serial_number=disk["SerialNumber"],
                        disk_number=disk["DiskNumber"],
                        bus_type=disk["BusType"],
                        size=disk["Size"],
                        unique_id=disk["UniqueId"],
                    )
                )
        else:
            self.add_error(
                "Could not get disks",
                metadata=ScanErrorMetadata(
                    identifier="Get-Disk",
                    stderr="\n".join(get_disks_cmd.stderr),
                ),
                error_type=ErrorTypeEnum.EXECUTION_ERROR,
                fatal=False,
            )

        computer_info_cmd = shell_executor.execute_pwsh_json(
            "Get-ComputerInfo | Select-Object -Property CsPhyicallyInstalledMemory, CsProcessors"
        )

        cpus = []
        memory_size = -1

        if computer_info_cmd.return_code == 0:
            for cpu in computer_info_cmd.data["CsProcessors"]:
                cpus.append(
                    WindowsCPU(
                        name=cpu[
                            "Name"
                        ].strip(),  # For some reason, this includes a ludicrous amount of whitespace
                        manufacturer=cpu["Manufacturer"],
                        num_cores=cpu["NumberOfCores"],
                        num_logical_cores=cpu["NumberOfLogicalProcessors"],
                        socket=cpu["SocketDesignation"],
                    )
                )

            memory_size = computer_info_cmd.data["CsPhyicallyInstalledMemory"]

        get_pnp_device_cmd = shell_executor.execute_pwsh_json("Get-PnPDevice")

        with open("dump.json", "w") as dump_file:
            dump_file.write(json.dumps(get_pnp_device_cmd.data))

        return WindowsHardware(disks=disks, cpus=cpus, memory_size=memory_size)
