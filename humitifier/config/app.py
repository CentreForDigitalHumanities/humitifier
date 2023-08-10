from dataclasses import dataclass
from functools import cached_property
from pssh.clients import ParallelSSHClient
from pssh.output import HostOutput
from humitifier.state.host_collection import HostCollectionState
from .host import HostConfig
from .facts import FactConfig
from .filterset import FiltersetConfig
from .host_view import HostViewConfig

@dataclass
class AppConfig:
    hosts: list[HostConfig]
    facts: FactConfig
    filters: FiltersetConfig
    default_view_cfg: HostViewConfig
    pssh_conf: dict[str, str]
    poll_interval: str

    @cached_property
    def host_kv(self):
        return {host.fqdn: host for host in self.hosts}

    
    def collect_outputs(self) -> list[HostOutput]:
        client = ParallelSSHClient(
            hosts=[host.fqdn for host in self.hosts],
            **self.pssh_conf
        )
        outputs = []
        for cmdset in self.facts.command_set(self.hosts):
            print(cmdset)
            outputs += client.run_command("%s", host_args=cmdset)
        client.join()
        return outputs
    
    
    def get_host_state_collection(self, outputs: list[HostOutput]) -> HostCollectionState:
        outputs = self.collect_outputs()
        return HostCollectionState.initialize(
            hosts=self.hosts,
            all_outputs=outputs,
            default_fact_cfg=self.facts,
            default_view_cfg=self.default_view_cfg
        )