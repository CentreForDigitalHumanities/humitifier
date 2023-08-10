from pssh.output import HostOutput

from humitifier.facts.protocols import SshFact
from humitifier.config.host import HostConfig

class FactConfig(set[type[SshFact]]):

    @property
    def fact_cls_kv(self) -> dict[str, type[SshFact]]:
        return {fact_cls.alias: fact_cls for fact_cls in self}
    
    def parse_output(self, host_output: HostOutput) -> SshFact:
        fact_alias, *stdout = list(host_output.stdout)
        fact_cls = self.fact_cls_kv[fact_alias]
        return fact_cls.from_stdout(stdout)
    
    @staticmethod
    def _wrap_host_cmd(cfg: HostConfig, fact: type[SshFact]) -> str:
        base = fact.ssh_command(cfg)
        return f"echo {fact.alias} && {base}"

    def command_set(self, hosts: list[HostConfig]) -> list[list[str]]:
        return [
            [self._wrap_host_cmd(host, fact) for host in hosts] for fact in self
        ]