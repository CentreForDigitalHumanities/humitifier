import asyncio
import time
import json
from pssh.output import HostOutput
from datetime import datetime
from humitifier.infra.facts import FACT_TABLE, DIVIDER, element_to_fact, HostnameCtl, Memory, Uptime, PackageList
from dataclasses import dataclass


@dataclass
class HostFacts:
    fqdn: str
    timestamp: int
    raw_output: str
    facts: dict
    exceptions: list[str] | None = None

    @classmethod
    async def from_output(cls, output: HostOutput, ts: int) -> "HostFacts":
        if output.exception:
            return cls(output.host, ts, None, {}, [str(output.exception)])
        stdout = "\n".join(list(output.stdout)).strip()
        elements = stdout.split(DIVIDER)
        tasks = [element_to_fact(el) for el in elements]
        parsed = await asyncio.gather(*tasks)
        facts = [f for f in parsed if not isinstance(f, str)]
        excpetions = [f for f in parsed if isinstance(f, str)]
        return cls(output.host, ts, stdout, {f.alias: f for f in facts}, excpetions or None)

    @property
    async def sql_row(self) -> str:
        fact_data = {k: fact.to_sql() for k, fact in self.facts.items()}
        return (
            self.fqdn,
            self.timestamp,
            self.raw_output,
            json.dumps(fact_data),
            json.dumps(self.exceptions),
        )

    @classmethod
    async def from_sql_row(cls, row) -> "HostFacts":
        fqdn, timestamp, raw_output, facts, exceptions = row
        fact_data = {k: FACT_TABLE[k].from_sql(v) for k, v in json.loads(facts).items()}
        return cls(fqdn, timestamp, raw_output, fact_data, json.loads(exceptions))

    @property
    def last_scan(self) -> str:
        ts = time.localtime(self.timestamp)
        current = time.localtime()
        minutes_ago = current.tm_min - ts.tm_min
        hours_ago = current.tm_hour - ts.tm_hour
        days_ago = current.tm_mday - ts.tm_mday
        time_ago_str = ""
        if days_ago > 0:
            time_ago_str += f"{days_ago} days "
        if hours_ago > 0:
            time_ago_str += f"{hours_ago} hours "
        if minutes_ago > 0:
            time_ago_str += f"{minutes_ago} minutes "
        if not time_ago_str:
            return "just now"
        return f"{time_ago_str}ago"

    @property
    def last_scan_dt(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)

    @property
    def os(self) -> str | None:
        if ctl := self.facts.get(HostnameCtl.alias):
            return ctl.os

    @property
    def hostname(self) -> str | None:
        if ctl := self.facts.get(HostnameCtl.alias):
            return ctl.hostname

    @property
    def memory_percentage(self) -> int | None:
        if memory := self.facts.get(Memory.alias):
            return memory.total_percent_use

    @property
    def memory_label(self) -> str | None:
        if memory := self.facts.get(Memory.alias):
            return f"{memory.used_mb}MB / {memory.total_mb}MB"

    @property
    def uptime_days(self) -> int | None:
        if uptime := self.facts.get(Uptime.alias):
            return uptime.days

    @property
    def packages(self) -> PackageList | None:
        return self.facts.get(PackageList.alias)
