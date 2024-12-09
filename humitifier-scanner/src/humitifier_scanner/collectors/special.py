from humitifier_common.facts import ZFS, ZFSPool, ZFSVolume
from humitifier_scanner.collectors import CollectInfo, ShellFactCollector
from humitifier_scanner.executor.linux_shell import LinuxShellExecutor


class ZFSVolumesFactCollector(ShellFactCollector):
    fact = ZFS

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> ZFS:
        pools = []
        volumes = []

        zpool_cmd = shell_executor.execute("/sbin/zpool list -p -H -o name,size,alloc")

        if zpool_cmd.return_code != 0:
            self.add_error("Failed to list zpools")
        else:
            for output_line in zpool_cmd.stdout:
                try:
                    name, size, used = output_line.strip().split()

                    size = self._parse_to_kb(size)
                    used = self._parse_to_kb(used)

                    pools.append(
                        ZFSPool(
                            name=name.strip(),
                            size_mb=size,
                            used_mb=used,
                        )
                    )
                except ValueError:
                    self.add_error("Failed to parse zpool list output")

        volumes_cmd = shell_executor.execute(
            "/sbin/zfs list -p -H -o name,used,avail,mountpoint"
        )

        if volumes_cmd.return_code != 0:
            self.add_error("Failed to list zfs volumes")
        else:
            for output_line in volumes_cmd.stdout:
                try:
                    name, used, available, mount = output_line.strip().split()

                    used = self._parse_to_kb(used)
                    available = self._parse_to_kb(available)

                    size = used + available

                    volumes.append(
                        ZFSVolume(
                            name=name.strip(),
                            size_mb=size,
                            used_mb=used,
                            mount=mount.strip(),
                        )
                    )
                except ValueError:
                    self.add_error("Failed to parse zfs list output")

        return ZFS(pools=pools, volumes=volumes)

    @staticmethod
    def _parse_to_kb(value: str) -> int:
        byte_value = int(value)
        return byte_value // 1024 // 1024
