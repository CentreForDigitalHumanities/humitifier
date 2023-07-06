import itertools
from pssh.clients import ParallelSSHClient
from pssh.output import HostOutput
from humitifier.infra.facts import Fact
from humitifier.config import AppConfig


def init_client(config: AppConfig) -> ParallelSSHClient:
    return ParallelSSHClient([h.fqdn for h in config.hosts], **config.pssh_conf)


def collect_facts(client: ParallelSSHClient, config: AppConfig) -> list[HostOutput]:
    outputs = []
    for f in config.facts:
        commands = [f.cmd(host) for host in config.hosts]
        outputs += client.run_command("%s", host_args=commands)
    client.join()
    return outputs


def parse_facts(outputs: list[HostOutput], config: AppConfig) -> dict[str, list[Fact]]:
    parsers = list(itertools.chain.from_iterable(itertools.repeat(fact, len(config.hosts)) for fact in config.facts))
    res = {}
    for fact, out in zip(parsers, outputs):
        host = out.host
        if host not in res:
            res[host] = []
        res[host].append(fact.from_stdout(list(out.stdout)))
    return res