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

from humitifier.utils import partial_match, flatten_list
from humitifier.models.host_state import HostState
from humitifier.properties import MetadataProperty, FactProperty

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
    
    @classmethod
    def from_key(cls, key: str) -> "Filter":
        return cls[key.capitalize()]
    
    @property
    def _property_extractor(self) -> MetadataProperty | FactProperty:
        match self:
            case Filter.Hostname:
                return FactProperty.Hostname
            case Filter.Os:
                return FactProperty.Os
            case Filter.Package:
                return FactProperty.PackagesNames
            case Filter.Department:
                return MetadataProperty.Department
            case Filter.Owner:
                return MetadataProperty.OwnerName
            case Filter.Purpose:
                return MetadataProperty.Purpose
            case Filter.Person:
                return MetadataProperty.PeopleNames

    def extract_value(self, host_state: HostState):
        return self._property_extractor.extract(host_state)

    def options(self, hosts: list[HostState]) -> list[str]:
        values = [self.extract_value(h) for h in hosts]
        if all(isinstance(v, list) for v in values):
            options = flatten_list(values)
        else:
            options = values
        return list(sorted(set(options)))


    def apply(self, host_state: HostState, query: str) -> bool:
        match self:
            case Filter.Person | Filter.Package:
                return partial_match(self.extract_value(host_state), query)
            case Filter.Hostname | Filter.Owner:
                return query in self.extract_value(host_state)
            case Filter.Os | Filter.Department | Filter.Purpose:
                return self.extract_value(host_state) == query    
    
    
    @staticmethod
    def apply_from_kv(host_states: list[HostState], filter_kv: dict[str, str]) -> list[HostState]:
        filters = [(Filter.from_key(k), query) for k, query in filter_kv.items()]
        return [h for h in host_states if all(f.apply(h, query) for f, query in filters)]
