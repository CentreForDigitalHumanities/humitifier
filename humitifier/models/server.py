from pydantic import BaseModel
from .issue import Issue
from .servicecontract import ServiceContract
from .factping import FactPing
from humitifier.infra.facts import Package


class Server(BaseModel):
    """
    An arbitrary server
    """

    service_contract: ServiceContract | None  # The service contract associated to the server. Example: ServiceContract(...)
    facts: FactPing

    @property
    def uptime_days(self) -> int:
        return self.facts.uptime.days

    @property
    def hostname(self) -> str:
        return self.facts.hostnamectl.hostname

    @property
    def fqdn(self) -> str:
        raise NotImplementedError

    @property
    def ip_address(self) -> str:
        raise NotImplementedError

    @property
    def cpu_total(self) -> int:
        raise NotImplementedError

    @property
    def memory_total(self) -> int:
        return self.facts.memory.total_mb

    @property
    def memory_usage(self) -> int:
        return self.facts.memory.used_mb

    @property
    def local_storage_total(self) -> float:
        return self.facts.blocks[0].size_mb

    @property
    def is_virtual(self) -> bool:
        return self.facts.hostnamectl.virtualization == "vmware"

    @property
    def os(self) -> str:
        return self.facts.hostnamectl.os

    @property
    def packages(self) -> list[Package]:
        return self.facts.packages

    @classmethod
    def create(cls, servicecontract: ServiceContract | None, facts: FactPing) -> "Server":
        return cls(
            service_contract=servicecontract,
            facts=facts,
        )

    @property
    def issues(self) -> list[Issue]:
        issues = []
        if not self.service_contract:
            issues.append(Issue.create_no_service_contract(self.hostname))
        return issues
