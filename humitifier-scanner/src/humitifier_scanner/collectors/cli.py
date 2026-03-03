from humitifier_common.artefacts import SecureBootKeys
from humitifier_scanner.collectors.backend import CollectInfo, ShellCollector
from humitifier_scanner.executor.linux_shell import LinuxShellExecutor


class SecureBootKeysFactCollector(ShellCollector):
    fact = SecureBootKeys

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> SecureBootKeys | None:

        try:
            result = shell_executor.execute("mokutil --db")
        except Exception as e:
            self.add_error(f"Failed to execute mokutil: {e}")
            return None

        # mokutil returns full details, we're only interested in the subject names
        keys = []
        for line in result.stdout:
            if "Subject:" in line:
                try:
                    _, key_name = line.split("CN=", maxsplit=1)
                    keys.append(key_name.strip())
                except ValueError:
                    # This is most likely a VMware key that thinks common names are
                    # not needed
                    self.add_error(f"Failed to parse key name: {line}", fatal=False)

        if result.return_code != 0:
            self.add_error(
                f"mokutil command failed with return code {result.return_code}"
            )
            return None

        return SecureBootKeys(keys=keys)
