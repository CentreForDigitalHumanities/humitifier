import asyncio
from .blocks import Blocks
from .groups import Groups
from .hostnamectl import HostnameCtl
from .memory import Memory
from .package_list import PackageList
from .uptime import Uptime
from .users import Users
from pssh.clients.native import ParallelSSHClient
from pssh.output import HostOutput
from typing import Union
from humitifier.config import CONFIG

DIVIDER = "================"
ALL_FACTS = [
    Blocks,
    Groups,
    HostnameCtl,
    Memory,
    PackageList,
    Uptime,
    Users,
]

Fact = Union[
    Blocks,
    Groups,
    HostnameCtl,
    Memory,
    PackageList,
    Uptime,
    Users,
]

FACT_TABLE = {
    Blocks.alias: Blocks,
    Groups.alias: Groups,
    HostnameCtl.alias: HostnameCtl,
    Memory.alias: Memory,
    PackageList.alias: PackageList,
    Uptime.alias: Uptime,
    Users.alias: Users,
}


async def create_host_cmd(host, facts: list[type[Fact]]) -> str:
    def fmt_cmd(fact: type[Fact]) -> str:
        echo = f"printf '{fact.alias}\n'"
        cmd = fact.ssh_command(host)
        return f"{echo} && {cmd}"

    echo_div = f"&& printf '{DIVIDER}\n' &&"
    cmd = echo_div.join([fmt_cmd(f) for f in facts])
    return cmd


async def host_cmd_set(hosts) -> list[str]:
    tasks = [create_host_cmd(host, ALL_FACTS) for host in hosts]
    return await asyncio.gather(*tasks)


async def element_to_fact(el: str) -> Fact:
    alias, *stdout = el.strip().split("\n")
    stdout = [out for out in stdout if out.strip()]
    try:
        fact = FACT_TABLE[alias]
    except KeyError as e:
        return f"ParseError(KeyError): {str(e)}"
    try:
        return fact.from_stdout(stdout)
    except Exception as e:
        return f"ParseError: {str(e)}"


async def query_inventory_outputs(hosts) -> list[HostOutput]:
    cmdset = await host_cmd_set(hosts)
    client = ParallelSSHClient([h.fqdn for h in hosts], **CONFIG.pssh)
    return client.run_command("%s", host_args=cmdset, stop_on_errors=False, read_timeout=10)
