from dataclasses import dataclass
from functools import cached_property
from pssh.clients import ParallelSSHClient
from pssh.output import HostOutput
from .host import HostConfig
from .facts import FactConfig
from .filterset import FiltersetConfig


@dataclass
class AppConfig:
    hosts: list[HostConfig]
    facts: FactConfig
    filters: FiltersetConfig
    pssh_conf: dict[str, str]
    poll_interval: str

    @cached_property
    def host_kv(self):
        return {host.fqdn: host for host in self.hosts}

    def collect_outputs(self) -> list[HostOutput]:
        client = ParallelSSHClient(hosts=[host.fqdn for host in self.hosts], **self.pssh_conf)
        outputs = []
        for cmdset in self.facts.command_set(self.hosts):
            print(cmdset)
            outputs += client.run_command("%s", host_args=cmdset)
        client.join()
        return outputs
