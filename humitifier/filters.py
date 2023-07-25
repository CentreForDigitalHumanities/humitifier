from humitifier.utils import partial_match, flatten_list
from humitifier.models.host_state import HostState
from humitifier.properties import facts, metadata
from humitifier.protocols import IFilter
from typing import Type

class HostnameFilter:
    slug = "hostname"
    label = "Hostname"
    widget = "search"

    @classmethod
    def options(cls, host_states: list[HostState]) -> list[str]:
        return [facts.Hostname.from_host_state(h).value for h in host_states]

    @classmethod
    def apply(cls, host_state: HostState, query: str) -> bool:
        return query in facts.Hostname.from_host_state(host_state).value


class OsFilter:
    slug = "os"
    label = "Operating System"
    widget = "select"

    @classmethod
    def options(cls, host_states: list[HostState]) -> list[str]:
        return [facts.Os.from_host_state(h).value for h in host_states]

    @classmethod
    def apply(cls, host_state: HostState, query: str) -> bool:
        return query == facts.Os.from_host_state(host_state).value


class PackageFilter:
    slug = "package"
    label = "Package"
    widget = "search"

    @classmethod
    def options(cls, host_states: list[HostState]) -> list[str]:
        packages = [facts.PackageList.from_host_state(h).value for h in host_states]
        return [p.name for p in flatten_list(packages)]

    @classmethod
    def apply(cls, host_state: HostState, query: str) -> bool:
        packages = facts.PackageList.from_host_state(host_state).value
        package_names = [p.name for p in packages]
        return partial_match(package_names, query)
    
class DepartmentFilter:
    slug = "department"
    label = "Department"
    widget = "select"

    @classmethod
    def options(cls, host_states: list[HostState]) -> list[str]:
        return [metadata.Department.from_host_state(h).value for h in host_states]

    @classmethod
    def apply(cls, host_state: HostState, query: str) -> bool:
        return query == metadata.Department.from_host_state(host_state).value
    
class OwnerFilter:
    slug = "owner"
    label = "Owner"
    widget = "search"

    @classmethod
    def options(cls, host_states: list[HostState]) -> list[str]:
        return [metadata.Owner.from_host_state(h).value.name for h in host_states]

    @classmethod
    def apply(cls, host_state: HostState, query: str) -> bool:
        return query in metadata.Owner.from_host_state(host_state).value.name
    
class PurposeFilter:
    slug = "purpose"
    label = "Purpose"
    widget = "select"

    @classmethod
    def options(cls, host_states: list[HostState]) -> list[str]:
        return [metadata.Purpose.from_host_state(h).value for h in host_states]

    @classmethod
    def apply(cls, host_state: HostState, query: str) -> bool:
        return query == metadata.Purpose.from_host_state(host_state).value
    
class PersonFilter:
    slug = "person"
    label = "Person"
    widget = "search"

    @classmethod
    def options(cls, host_states: list[HostState]) -> list[str]:
        people = [metadata.People.from_host_state(h).value for h in host_states]
        return [p.name for p in flatten_list(people)]

    @classmethod
    def apply(cls, host_state: HostState, query: str) -> bool:
        people = metadata.People.from_host_state(host_state).value
        return partial_match([p.name for p in people], query)

def filter_options(options: list[str]) -> list[str]:
    return list(sorted(set(options)))


def apply_from_query_params(host_states: list[HostState], query_params: dict[str, str], filter_kv: dict[str, Type[IFilter]]) -> list[HostState]:
    filters = [(filter_kv[k], query) for k, query in query_params.items()]
    return [h for h in host_states if all(f.apply(h, query) for f, query in filters)]

