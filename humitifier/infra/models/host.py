import os
import toml
from datetime import datetime
from dataclasses import dataclass
from typing import Iterable
from humitifier.config import CONFIG
from humitifier.infra.alerts import ALERTS
from .hostfacts import HostFacts


@dataclass
class Host:
    fqdn: str
    metadata: dict
    facts: HostFacts | None = None

    @classmethod
    def load_inventory(cls) -> Iterable["Host"]:
        for f in os.listdir(CONFIG.inventory):
            if f.endswith(".toml"):
                with open(os.path.join(CONFIG.inventory, f)) as fh:
                    data = toml.load(fh)
                    for k, v in data.items():
                        yield cls(fqdn=k, metadata=v)

    @property
    def os(self) -> str:
        return self.facts.os

    @property
    def alerts(self) -> list:
        all_alerts = {alert.__name__: alert(self) for alert in ALERTS}
        return [(code, a[0], a[1]) for code, a in all_alerts.items() if a]

    @property
    def alert_codes(self) -> list:
        return [code for code, _, _ in self.alerts]

    @property
    def alert_count(self) -> int:
        return len(self.alerts)

    @property
    def alert_severity(self) -> str:
        severities = {s for _, s, _ in self.alerts}
        if "critical" in severities:
            return "critical"
        elif "warning" in severities:
            return "warning"
        elif "info" in severities:
            return "info"
        else:
            return "ok"

    @property
    def department(self) -> str | None:
        return self.metadata.get("department")

    @property
    def contact(self) -> str | None:
        if contact := self.metadata.get("contact"):
            return contact.get("name"), contact.get("email")

    @property
    def package_names(self) -> list[str]:
        if packages := self.facts.packages:
            return [p.name for p in packages]

    @property
    def last_scan_dt(self) -> datetime:
        return datetime.fromtimestamp(self.facts.timestamp)

    @property
    def last_scan_dt_iso(self) -> datetime:
        return self.last_scan_dt.isoformat(" ") if self.facts else "Not scanned yet"

    @property
    def meta_props(self) -> list[tuple[str, str]]:
        ignore = ["department"]
        return [(k, v) for k, v in self.metadata.items() if isinstance(v, str) and k not in ignore]
