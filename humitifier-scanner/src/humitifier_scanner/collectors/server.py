import json
from datetime import datetime

from humitifier_scanner.collectors import CollectInfo, ShellFactCollector, T
from humitifier_scanner.executor.linux_shell import LinuxShellExecutor
from humitifier_common.facts import HostMeta, IsWordpress, PuppetAgentStatus, Uptime


class HostMetaFactCollector(ShellFactCollector):
    fact = HostMeta

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> HostMeta:
        result = shell_executor.execute("cat /hum/doc/server_facts.json")

        if result.return_code != 0:
            return HostMeta()

        json_str = "\n".join(result.stdout)
        json_args = json.loads(json_str)

        return HostMeta(**json_args)


class UptimeFactCollector(ShellFactCollector):
    fact = Uptime

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> Uptime:
        result = shell_executor.execute("uptime -s")

        dt = datetime.fromisoformat(result.stdout[0].strip())
        now = datetime.now()

        return Uptime((now - dt).total_seconds())


class PuppetAgentStatusFactCollector(ShellFactCollector):
    fact = PuppetAgentStatus

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> PuppetAgentStatus:
        # We use a neg-check for slightly less mental stress
        # TODO: this does not work due to permission errors. FIX!
        result = shell_executor.execute(
            "test ! -f /opt/puppetlabs/puppet/cache/state/agent_disabled.lock"
        )

        # Puppet is disabled if the test command 'fails'; in other words,
        # Puppet is disabled if the status code is not 0.
        return PuppetAgentStatus(disabled=result.return_code != 0)


class IsWordpressFactCollector(ShellFactCollector):
    fact = IsWordpress

    required_facts = [HostMeta]

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> IsWordpress:

        host_meta: HostMeta = info.required_facts.get(HostMeta)

        if host_meta.vhosts:
            for vhost in host_meta.vhosts:
                for site, info in vhost.items():
                    result = shell_executor.execute(
                        f"find {info['docroot']} -maxdepth 1 -name wp-config.php -print -quit"
                    )
                    if result.return_code == 0:
                        return IsWordpress(is_wp=True)

        return IsWordpress(is_wp=False)
