from pssh.output import HostOutput

from humitifier.facts.protocols import SshFact
from humitifier.config.host import HostConfig

DIVIDER = "================"


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
        return [[self._wrap_host_cmd(host, fact) for host in hosts] for fact in self]

    def initialize_host_fact_data(self, host_outputs: list[HostOutput]):
        facts = (self.parse_output(out) for out in host_outputs)
        return {fact.alias: fact for fact in facts}

    def wrap_for_host(self, host_cfg: HostConfig) -> str:
        def _wrap_fact(fact) -> str:
            base = fact.ssh_command(host_cfg)
            return f"echo {fact.alias} && {base}"

        host_facts = [_wrap_fact(f) for f in self]
        div_echo = f"&& echo {DIVIDER} &&"
        return div_echo.join(host_facts)
