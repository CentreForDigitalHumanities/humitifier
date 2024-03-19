import asyncpg
import json
from dataclasses import dataclass
from itertools import groupby

from humitifier import facts
from humitifier.alerts import ALERTS
from humitifier.config import CONFIG
from humitifier.logging import logging
from humitifier.utils import FactError

logger = logging.getLogger(__name__)


@dataclass
class Facts:
    Blocks: facts.Blocks | FactError
    Groups: facts.Groups | FactError
    HostMeta: facts.HostMeta | FactError
    HostnameCtl: facts.HostnameCtl | FactError
    Memory: facts.Memory | FactError
    PackageList: facts.PackageList | FactError
    Uptime: facts.Uptime | FactError
    Users: facts.Users | FactError
    PuppetAgentStatus: facts.PuppetAgentStatus | FactError

    @classmethod
    def from_sql_rows(cls, rows):
        create_args = {}
        for row in rows:
            name = row["name"]
            data = json.loads(row["data"])
            try:
                parser = getattr(facts, name)
                create_args[name] = parser.from_sql(data)
            except Exception as e:
                logger.info(f"Error parsing {name}: {e}")
                create_args[name] = FactError(**data)
        try:
            return cls(**create_args)
        except TypeError:
            not_collected_fact_err = FactError(
                stdout="",
                stderr="",
                exception="",
                exit_code=0,
                py_excpetion="Fact Not Collected",
            )
            err_args_base = {k: not_collected_fact_err for k in cls.__annotations__}
            err_args = {**err_args_base, **create_args}
            return cls(**err_args)


@dataclass
class Host:
    fqdn: str
    facts: Facts

    @property
    def os(self):
        if isinstance(fact := self.facts.HostnameCtl, FactError):
            return None
        return fact.os

    @property
    def department(self):
        if isinstance(fact := self.facts.HostMeta, FactError):
            return None
        return fact.department

    @property
    def contact(self):
        if isinstance(fact := self.facts.HostMeta, FactError):
            return None
        return fact.contact

    @property
    def packages(self):
        if isinstance(fact := self.facts.PackageList, FactError):
            return []
        return fact

    @property
    def hostname(self):
        if isinstance(fact := self.facts.HostnameCtl, FactError):
            return None
        return fact.hostname

    @property
    def webdav(self):
        if isinstance(fact := self.facts.HostMeta, FactError):
            return None
        return fact.webdav

    @property
    def vhosts(self):
        if isinstance(fact := self.facts.HostMeta, FactError):
            return None
        return fact.vhosts

    @property
    def fileservers(self):
        if isinstance(fact := self.facts.HostMeta, FactError):
            return None
        return fact.fileservers

    @property
    def databases(self):
        if isinstance(fact := self.facts.HostMeta, FactError):
            return None
        return fact.databases

    @property
    def alert_codes(self):
        return {a for a, _, _ in self.alerts}

    @property
    def alerts(self):
        return [(a.__name__, a_res, a.__doc__) for a in ALERTS if (a_res := a(self))]

    @property
    def severity(self):
        severities = {x[1] for x in self.alerts}
        if "critical" in severities:
            return "critical"
        elif "warning" in severities:
            return "warning"
        elif "info" in severities:
            return "info"
        else:
            return None


async def get_hosts() -> list[Host]:
    conn = await asyncpg.connect(CONFIG.db)
    rows = await conn.fetch(
        "SELECT name, host, scan, data FROM facts WHERE scan = (SELECT MAX(scan) FROM facts) ORDER BY host"
    )
    hosts = []
    for fqdn, facts in groupby(rows, key=lambda row: row["host"]):
        facts = Facts.from_sql_rows(facts)
        hosts.append(Host(fqdn, facts))
    return hosts
