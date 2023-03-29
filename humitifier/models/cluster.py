from pydantic import BaseModel
from .server import Server
from humitifier.utils import partial_match, flatten_list


class Cluster(BaseModel):
    name: str
    servers: list[Server]

    def apply_filters(self, **kwargs) -> list[Server]:
        servers = self.servers
        for filtername, value in kwargs.items():
            if value:
                func = getattr(Cluster, f"_filter_by_{filtername}")
                servers = func(servers, value)
        return servers

    def get_server_by_hostname(self, hostname: str) -> Server:
        servers = [s for s in self.servers if s.hostname == hostname]
        if len(servers) > 1:
            raise ValueError(f"More than one server with hostname {hostname}")
        return servers[0]

    @staticmethod
    def opts(servers: list[Server]) -> dict[str, list[str]]:
        return {
            "hostname": [s.hostname for s in servers],
            "os": list(set([s.os for s in servers])),
            "entity": list(set([s.service_contract.entity for s in servers if s.service_contract])),
            "owner": list(set([s.service_contract.owner.name for s in servers if s.service_contract])),
            "purpose": list(set([s.service_contract.purpose for s in servers if s.service_contract])),
            "package": list(set([p.name for p in flatten_list([s.packages for s in servers])])),
            "contact": list(
                set([p.name for p in flatten_list([s.service_contract.people for s in servers if s.service_contract])])
            ),
            "issue": list(set([i.slug for i in flatten_list([s.issues for s in servers])])),
        }

    @staticmethod
    def _filter_by_hostname(servers: list[Server], query: str) -> list[Server]:
        return [s for s in servers if query in s.hostname]

    @staticmethod
    def _filter_by_os(servers: list[Server], query: str) -> list[Server]:
        return [s for s in servers if query in s.os]

    @staticmethod
    def _filter_by_entity(servers: list[Server], query: str) -> list[Server]:
        return [s for s in servers if query in s.service_contract.entity]

    @staticmethod
    def _filter_by_owner(servers: list[Server], query: str) -> list[Server]:
        return [s for s in servers if query in s.service_contract.owner.name]

    @staticmethod
    def _filter_by_purpose(servers: list[Server], query: str) -> list[Server]:
        return [s for s in servers if query == s.service_contract.purpose]

    @staticmethod
    def _filter_by_package(servers: list[Server], query: str) -> list[Server]:
        return [s for s in servers if partial_match([p.name for p in s.packages], query)]

    @staticmethod
    def _filter_by_contact(servers: list[Server], query: str) -> list[Server]:
        return [s for s in servers if partial_match([p.name for p in s.service_contract.people], query)]

    @staticmethod
    def _filter_by_issue(servers: list[Server], query: str) -> list[Server]:
        return [s for s in servers if query in [i.slug for i in s.issues]]
