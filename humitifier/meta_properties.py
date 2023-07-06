from datetime import date
from humitifier.models.host import Host
from humitifier.models.person import Person

from typing import Protocol


class MetaProp(Protocol):
    key: str

    def __call__(self, host: Host): ...


class Department:
    key = "department"

    def __call__(self, host: Host):
        return host.metadata["department"]
    

class Owner:
    key = "owner"

    def __call__(self, host: Host):
        return Person(**host.metadata["owner"])
    

class StartDate:
    key = "start_date"

    def __call__(self, host: Host):
        return date.fromisoformat(host.metadata["start_date"])
    

class EndDate:
    key = "end_date"

    def __call__(self, host: Host):
        return date.fromisoformat(host.metadata["end_date"])
    
class Purpose:
    key = "purpose"

    def __call__(self, host: Host):
        return host.metadata["purpose"]
    
class People:
    key = "people"

    def __call__(self, host: Host):
        return [Person(**p) for p in host.metadata["people"]]