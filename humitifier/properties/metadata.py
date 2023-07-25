from dataclasses import dataclass
from datetime import date

from humitifier.protocols import IProperty
from humitifier.models.person import Person
from humitifier.models.host_state import HostState
from humitifier.views.atoms import MailToPerson, UnorderedList


@dataclass
class Department(IProperty):
    value: str
    kv_label: str = "Department"

    @classmethod
    def slug(cls) -> str:
        return "department"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "Department":
        return cls(host_state.host.metadata["department"])

    def render_kv_value(self) -> str:
        return self.value
    

@dataclass
class Owner(IProperty):
    value: Person
    kv_label: str = "Owner"

    @classmethod
    def slug(cls) -> str:
        return "owner"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "Owner":
        return cls(value=Person(**host_state.host.metadata["owner"]))

    def render_kv_value(self) -> str:
        return MailToPerson(person=self.value).render()
    

@dataclass
class StartDate(IProperty):
    value: date
    kv_label: str = "Start Date"

    @classmethod
    def slug(cls) -> str:
        return "start_date"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "StartDate":
        return cls(value=date.fromisoformat(host_state.host.metadata["start_date"]))

    def render_kv_value(self) -> str:
        return self.value.isoformat()
    
@dataclass
class EndDate(IProperty):
    value: date
    kv_label: str = "End Date"

    @classmethod
    def slug(cls) -> str:
        return "end_date"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "EndDate":
        return cls(value=date.fromisoformat(host_state.host.metadata["end_date"]))

    def render_kv_value(self) -> str:
        return self.value.isoformat()


@dataclass
class RetireIn(IProperty):
    value: int
    kv_label: str = "Retire In"

    @classmethod
    def slug(cls) -> str:
        return "retire_in"
    
    @classmethod
    def from_host_state(cls, host_state: HostState) -> "RetireIn":
        end_date = date.fromisoformat(host_state.host.metadata["end_date"])
        return cls(value=(end_date - date.today()).days)
    
    def render_kv_value(self) -> str:
        return f"{self.value} days"
    

@dataclass
class Purpose(IProperty):
    value: str
    kv_label: str = "Purpose"

    @classmethod
    def slug(cls) -> str:
        return "purpose"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "Purpose":
        return cls(value=host_state.host.metadata["purpose"])

    def render_kv_value(self) -> str:
        return self.value
    

@dataclass
class People(IProperty):
    value: list[Person]
    kv_label: str = "Affiliates"

    @classmethod
    def slug(cls) -> str:
        return "people"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "People":
        return cls(value=[Person(**p) for p in host_state.host.metadata["people"]])

    def render_kv_value(self) -> str:
        elements = [MailToPerson(person=p).render() for p in self.value]
        return UnorderedList(items=elements).render()