import itertools
from functools import cached_property
from pssh.clients import ParallelSSHClient
from pssh.output import HostOutput
from pssh.config import HostConfig
from typing import Type
from dataclasses import dataclass
from . import facts

HostList = list[str]
HostConfigList = list[HostConfig]
FactList = list[Type[facts.Fact]]
PsshArgs = tuple[HostList, HostConfigList, FactList]


@dataclass
class PsshBuilder:
    """Build pssh client arguments for specified hosts and facts"""

    hosts: list[str]
    facts: list[Type[facts.Fact]]

    @cached_property
    def host_fact_product(self) -> list[tuple[str, Type[facts.Fact]]]:
        """Generate list of tuples of host and fact for all specified hosts and facts"""
        return list(itertools.product(self.hosts, self.facts))

    @cached_property
    def configs(self) -> list[HostConfig]:
        """Generate list of HostConfig objects for all specified hosts"""
        return [HostConfig(alias=fact.__name__) for _, fact in self.host_fact_product]

    @cached_property
    def client_hosts(self) -> list[str]:
        """Generate list of hosts with fact name as alias"""
        return [host for host, _ in self.host_fact_product]

    @cached_property
    def commands(self) -> list[str]:
        """Generate list of commands for all specified facts"""
        return [generate_cmd(fact, host) for host, fact in self.host_fact_product]

    def client(self, **client_kwargs) -> ParallelSSHClient:
        """Generate pssh client with specified arguments"""
        return ParallelSSHClient(self.client_hosts, host_config=self.configs, **client_kwargs)

    def run(self, client: ParallelSSHClient) -> list[HostOutput]:
        """Run pssh client with specified arguments and return list of HostOutput objects"""
        outputs = client.run_command("%s", host_args=self.commands)
        client.join()
        return outputs


def generate_cmd(fact_type: Type[facts.Fact], host: str) -> str:
    match fact_type:
        case facts.HostnameCtl:
            return "hostnamectl"
        case facts.Memory:
            return "free -m"
        case facts.Package:
            return (
                "command -v dpkg-query >/dev/null 2>&1 && "
                "dpkg-query -W -f='${Package}\t${Version}\n' || "
                "rpm -qa --queryformat '%{NAME}\t%{VERSION}\n'"
            )
        case facts.Block:
            return "df -m"
        case facts.Uptime:
            return "uptime -p"
        case facts.Group:
            return "cat /etc/group"
        case facts.User:
            return "cat /etc/passwd"


def parse_output(output: HostOutput) -> facts.Fact:
    """Parse output of pssh client and return fact object"""
    if output.exit_code != 0:
        raise RuntimeError(f"Error running command on host {output.host}: {output.stderr}")
    fact_type = getattr(facts, output.alias)
    return fact_type.from_stdout(list(output.stdout))
