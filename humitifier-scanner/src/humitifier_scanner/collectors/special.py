from humitifier_common.artefacts import ZFS, ZFSPool, ZFSVolume
from humitifier_scanner.collectors import CollectInfo, ShellCollector
from humitifier_scanner.executor.linux_shell import LinuxShellExecutor


class ZFSVolumesMetricCollector(ShellCollector):
    metric = ZFS

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> ZFS | None:
        pools = []
        volumes = []

        zpool_cmd = shell_executor.execute("/sbin/zpool list -p -H -o name,size,alloc")

        if zpool_cmd.return_code != 0:
            self.add_error("Failed to list zpools")
        else:
            for output_line in zpool_cmd.stdout:
                try:
                    name, size, allocated = output_line.strip().split()

                    size = self._parse_to_mb(size)
                    allocated = self._parse_to_mb(allocated)

                    pools.append(
                        ZFSPool(
                            name=name.strip(),
                            size_mb=size,
                            used_mb=allocated,
                        )
                    )
                except ValueError:
                    self.add_error("Failed to parse zpool list output")

        volumes_cmd = shell_executor.execute(
            "/sbin/zfs list -p -H -o name,refer,avail,mountpoint"
        )

        if volumes_cmd.return_code != 0:
            self.add_error("Failed to list zfs volumes")
        else:
            for output_line in volumes_cmd.stdout:
                try:
                    name, referred, available, mount = output_line.strip().split()

                    referred = self._parse_to_mb(referred)
                    available = self._parse_to_mb(available)

                    size = referred + available

                    volumes.append(
                        ZFSVolume(
                            name=name.strip(),
                            size_mb=size,
                            used_mb=referred,
                            mount=mount.strip(),
                        )
                    )
                except ValueError:
                    self.add_error("Failed to parse zfs list output")

        # Don't return anything if we didn't find any pools nor any volumes
        if not pools and not volumes:
            return None

        return ZFS(pools=pools, volumes=volumes)

    @staticmethod
    def _parse_to_mb(value: str) -> int:
        byte_value = int(value)
        return byte_value // 1024 // 1024
