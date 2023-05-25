import itertools
from functools import cached_property
from pssh.clients import ParallelSSHClient
from pssh.output import HostOutput
from typing import Type
from dataclasses import dataclass
from . import facts


@dataclass
class PsshBuilder:
    """Build pssh client arguments for specified hosts and facts"""

    hosts: list[str]
    facts: list[Type[facts.Fact]]

    @cached_property
    def parsers(self) -> list[Type[facts.Fact]]:
        """Return list of parsers for specified facts"""
        return list(itertools.chain.from_iterable(itertools.repeat(fact, len(self.hosts)) for fact in self.facts))

    @cached_property
    def host_lookup(self) -> list[str]:
        """Return list of hosts for specified facts"""

        return list(itertools.chain(*[self.hosts for _ in self.facts]))

    def client(self, **client_kwargs) -> ParallelSSHClient:
        """Generate pssh client with specified arguments"""
        return ParallelSSHClient(self.hosts, **client_kwargs)

    def run(self, client: ParallelSSHClient) -> list[HostOutput]:
        """Run pssh client with specified arguments and return list of HostOutput objects"""
        outputs = []
        for f in self.facts:
            commands = [generate_cmd(f, host) for host in self.hosts]
            outputs += client.run_command("%s", host_args=commands)
        client.join()
        return outputs

    def parse(self, outputs: list[HostOutput]) -> dict[str, list[facts.Fact]]:
        """Parse list of HostOutput objects and return dict of host to Fact objects"""
        res = {}
        for fact, out in zip(self.parsers, outputs):
            host = out.host
            if host not in res:
                res[host] = []
            res[host].append(fact.from_stdout(list(out.stdout)))
        return res


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
