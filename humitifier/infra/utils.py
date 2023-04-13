from pssh.clients import ParallelSSHClient
from pssh.output import HostOutput
from pssh.config import HostConfig
from . import facts
from typing import Type

HostList = list[str]
HostConfigList = list[HostConfig]
CommandList = list[str]
PsshArgs = tuple[HostList, HostConfigList, CommandList]


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


def pssh_args_all_facts(hosts: list[str]) -> PsshArgs:
    """Generate arguments for pssh client to get all facts for all specified hosts"""
    collection = []
    for host in hosts:
        for fact_type in facts.Fact.__args__:
            collection.append((host, HostConfig(alias=fact_type.__name__), generate_cmd(fact_type, host)))
    return [x[0] for x in collection], [x[1] for x in collection], [x[2] for x in collection]


def collect_outputs(args: PsshArgs, **client_args) -> list[HostOutput]:
    """Run pssh client with specified arguments and return list of HostOutput objects"""
    client = ParallelSSHClient(args[0], host_config=args[1], **client_args)
    outputs = client.run_command("%s", host_args=args[2])
    client.join()
    return outputs


def parse_output(output: HostOutput) -> facts.Fact:
    """Parse output of pssh client and return fact object"""
    fact_type = getattr(facts, output.alias)
    return fact_type.from_stdout(output.stdout)
