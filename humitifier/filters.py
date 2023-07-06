from humitifier.models.host import Host
from humitifier.models.factping import FactPing
from humitifier.utils import partial_match, flatten_list

from typing import Literal, Protocol


class Filter(Protocol):
    slug: str
    name: str
    widget: Literal["select", "search"]


    def __call__(self, host: Host, host_facts: FactPing, query: str) -> bool: ...

    @staticmethod
    def options(hosts: list[tuple[Host, FactPing]]) -> list[str]: ...

class HostFilter:
    slug = "hostname"
    name = "Hostname"
    widget = "search"

    def __call__(self, host: Host, host_facts: FactPing, query: str) -> bool:
        return host_facts.hostname and query in host_facts.hostname
    
    @staticmethod
    def options(hosts: list[tuple[Host, FactPing]]) -> list[str]:
        return [host_facts.hostname for _, host_facts in hosts if host_facts.hostname]
    

class OsFilter:
    slug = "os"
    name = "Operating System"
    widget = "select"

    def __call__(self, host: Host, host_facts: FactPing, query: str) -> bool:
        return host_facts.os and query in host_facts.os
    
    @staticmethod
    def options(hosts: list[tuple[Host, FactPing]]) -> list[str]:
        return list(set([host_facts.os for _, host_facts in hosts if host_facts.os]))
    

class PackageFilter:
    slug = "package"
    name = "Package"
    widget = "search"

    def __call__(self, host: Host, host_facts: FactPing, query: str) -> bool:
        return host_facts.packages and partial_match([p.name for p in host_facts.packages], query)
    
    @staticmethod
    def options(hosts: list[tuple[Host, FactPing]]) -> list[str]:
        package_lists = [host_facts.packages for _, host_facts in hosts if host_facts.packages]
        all_packages = flatten_list(package_lists)
        return list(set([p.name for p in all_packages]))
    

class DepartmentFilter:
    slug = "department"
    name = "Department"
    widget = "select"

    def __call__(self, host: Host, host_facts: FactPing, query: str) -> bool:
        if not host.metadata or not host.metadata["department"]:
            return False
        return query in host.metadata["department"]
    
    @staticmethod
    def options(hosts: list[tuple[Host, FactPing]]) -> list[str]:
        departments = [host.metadata["department"] for host, _ in hosts if host.metadata and host.metadata.get("department")]
        return list(set(departments))
    

class OwnerFilter:
    slug = "owner"
    name = "Owner"
    widget = "search"

    def __call__(self, host: Host, host_facts: FactPing, query: str) -> bool:
        if not host.metadata or not getattr(host.metadata, "owner", None):
            return False
        return query in host.metadata["owner"]["name"]
    
    @staticmethod
    def options(hosts: list[tuple[Host, FactPing]]) -> list[str]:
        owners = [host.metadata["owner"]["name"] for host, _ in hosts if host.metadata and host.metadata["owner"]]
        return list(set(owners))
    

class PurposeFilter:
    slug = "purpose"
    name = "Purpose"
    widget = "select"

    def __call__(self, host: Host, host_facts: FactPing, query: str) -> bool:
        if not host.metadata or not host.metadata.get("purpose"):
            return False
        return query in host.metadata["purpose"]
    
    @staticmethod
    def options(hosts: list[tuple[Host, FactPing]]) -> list[str]:
        purposes = [host.metadata["purpose"] for host, _ in hosts if host.metadata and host.metadata.get("purpose")]
        return list(set(purposes))
    

class PersonFilter:
    slug = "person"
    name = "Person"
    widget = "search"

    def __call__(self, host: Host, host_facts: FactPing, query: str) -> bool:
        if not host.metadata or not host.metadata.get("people"):
            return False
        return partial_match([p["name"] for p in host.metadata["people"]], query)
    
    @staticmethod
    def options(hosts: list[tuple[Host, FactPing]]) -> list[str]:
        person_lists = [host.metadata["people"] for host, _ in hosts if host.metadata and host.metadata.get("people")]
        all_people = flatten_list(person_lists)
        return list(set([p["name"] for p in all_people]))