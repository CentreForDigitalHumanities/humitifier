"""Filters act as a way to filter the hosts based on a specific criteria.
The filters can be extend so long as they provide the same interface as the currently implemented filter, meaning they have:
- a `slug` property that returns a string
- a `label` property that returns a string
- a `widget` property that returns a string
- an `options` method that returns a list of strings
- an `apply` method that takes a list of HostState and query and returns a bool
- a `from_key` method that takes a string and returns a Filter
"""

from enum import Enum, auto

from humitifier.models.host_state import HostState
from humitifier.utils import partial_match, flatten_list

from typing import Literal


class Filter(Enum):
    Hostname = auto()
    Os = auto()
    Package = auto()
    Department = auto()
    Owner = auto()
    Purpose = auto()
    Person = auto()

    @property
    def widget(self) -> Literal["search", "select"]:
        match self:
            case Filter.Hostname | Filter.Package | Filter.Owner | Filter.Person:
                return "search"
            case Filter.Os | Filter.Department | Filter.Purpose:
                return "select"
            
    @property
    def label(self) -> str:
        return self.name.capitalize()
    
    @property
    def slug(self) -> str:
        return self.name.lower()
            

    def options(self, hosts: list[HostState]) -> list[str]:
        match self:
            case Filter.Hostname:
                options = [h.facts.hostname for h in hosts if h.facts.hostname]
            case Filter.Os:
                options = [h.facts.os for h in hosts if h.facts.os]
            case Filter.Package:
                packages = flatten_list([h.facts.packages for h in hosts])
                options = [p.name for p in packages]
            case Filter.Department:
                options = [h.host.metadata["department"] for h in hosts if h.host.metadata["department"]]
            case Filter.Owner:
                options = [h.host.metadata["owner"]["name"] for h in hosts if h.host.metadata["owner"]["name"]]
            case Filter.Purpose:
                options = [h.host.metadata["purpose"] for h in hosts if h.host.metadata["purpose"]]
            case Filter.Person:
                person_lists = [h.host.metadata["people"] for h in hosts if h.host.metadata and h.host.metadata.get("people")]
                all_people = flatten_list(person_lists)
                options = [p["name"] for p in all_people]
        return list(sorted(set(options)))


    def apply(self, host_state: HostState, query: str) -> bool:
        match self:
            case Filter.Hostname:
                return host_state.facts.hostname and query in host_state.facts.hostname
            case Filter.Os:
                return host_state.facts.os and query in host_state.facts.os
            case Filter.Package:
                return host_state.facts.packages and partial_match([p.name for p in host_state.facts.packages], query)
            case Filter.Department:
                if not host_state.host.metadata or not host_state.host.metadata["department"]:
                    return False
                return query in host_state.host.metadata["department"]
            case Filter.Owner:
                if not host_state.host.metadata or not getattr(host_state.host.metadata, "owner", None):
                    return False
                return query in host_state.host.metadata["owner"]["name"]
            case Filter.Purpose:
                if not host_state.host.metadata or not host_state.host.metadata.get("purpose"):
                    return False
                return query in host_state.host.metadata["purpose"]
            case Filter.Person:
                if not host_state.host.metadata or not host_state.host.metadata.get("people"):
                    return False
                return partial_match([p["name"] for p in host_state.host.metadata["people"]], query)

    @classmethod
    def from_key(cls, key: str) -> "Filter":
        return cls[key.capitalize()]
    
    
    @staticmethod
    def apply_from_kv(host_states: list[HostState], filter_kv: dict[str, str]) -> list[HostState]:
        filtered = host_states
        for filter_key, query in filter_kv.items():
            filter = Filter.from_key(filter_key)
            filtered = [h for h in filtered if filter.apply(h, query)]
        return filtered