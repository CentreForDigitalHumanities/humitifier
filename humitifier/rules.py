from typing import Protocol

from humitifier.models.host import Host
from humitifier.models.factping import FactPing
from humitifier.models.issue import Issue


class Rule(Protocol):
    slug: str
    name: str

    def __call__(self, host: Host, host_facts: FactPing) -> Issue: ...