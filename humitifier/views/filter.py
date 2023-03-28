from pydantic import BaseModel
from humitifier.models import Server
from humitifier.utils import flatten_list


class ServerFilter(BaseModel):
    servers: list[Server]

    @property
    def hostname_opts(self) -> list[str]:
        return [s.name for s in self.servers]

    @property
    def os_opts(self) -> list[str]:
        return list(set([s.os for s in self.servers]))

    @property
    def department_opts(self) -> list[str]:
        return list(set([s.service_contract.entity for s in self.servers]))

    @property
    def users_opts(self) -> list[str]:
        all_users = [s.users for s in self.servers]
        return list(set(flatten_list(all_users)))

    @property
    def group_opts(self) -> list[str]:
        all_groups = [s.groups for s in self.servers]
        return list(set(flatten_list(all_groups)))

    @property
    def package_opts(self) -> list[str]:
        all_packages = [s.packages for s in self.servers]
        return list(set([p.name for p in flatten_list(all_packages)]))

    @property
    def people_opts(self) -> list[str]:
        all_people = [s.service_contract.people for s in self.servers]
        all_people = [p.name for p in flatten_list(all_people)]
        return list(set(all_people))

    @property
    def owners_opts(self) -> list[str]:
        all_owners = [s.service_contract.owner.name for s in self.servers]
        return list(set(all_owners))

    @property
    def purpose_opts(self) -> list[str]:
        return list(set([s.service_contract.purpose for s in self.servers]))
