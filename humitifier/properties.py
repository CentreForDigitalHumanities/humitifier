"""Properties function as extendible ways of extracting data from a host state.
You can extend or implement them manually as long as you follow the protocol as below, meaning a property has:
- an `extract` method that takes a HostState and returns a value
- a `kv_atom` property that returns a valid Atom
- a `kv_label` property that returns a string
"""

from datetime import date
from enum import Enum, auto

from humitifier.models.host_state import HostState
from humitifier.models.person import Person
from humitifier.views.utils import Atom

class PropertyReadError(Exception): ...

class MetadataProperty(Enum):
    Department = auto()
    Owner = auto()
    OwnerName = auto()
    StartDate = auto()
    EndDate = auto()
    RetireIn = auto()
    Purpose = auto()
    People = auto()
    PeopleNames = auto()

    def extract(self, host_state: HostState):
        try:
            match self:
                case MetadataProperty.Department:
                    return host_state.host.metadata["department"]
                case MetadataProperty.Owner:
                    return Person(**host_state.host.metadata["owner"])
                case MetadataProperty.OwnerName:
                    return MetadataProperty.Owner.extract(host_state).name
                case MetadataProperty.StartDate:
                    return date.fromisoformat(host_state.host.metadata["start_date"])
                case MetadataProperty.EndDate:
                    return date.fromisoformat(host_state.host.metadata["end_date"])
                case MetadataProperty.RetireIn:
                    end_date = date.fromisoformat(host_state.host.metadata["end_date"])
                    return (end_date - date.today()).days
                case MetadataProperty.Purpose:
                    return host_state.host.metadata["purpose"]
                case MetadataProperty.People:
                    return [Person(**p) for p in host_state.host.metadata["people"]]
                case MetadataProperty.PeopleNames:
                    return [p.name for p in MetadataProperty.People.extract(host_state)]
        except KeyError as e:
            raise PropertyReadError(f"The {self.name} property could not be accessed from the metadata. Make sure the metadata has the corresponding key") from e
            
    @property
    def kv_atom(self) -> Atom:
        match self:
            case MetadataProperty.People:
                return Atom.MailToPeopleList
            case MetadataProperty.Owner:
                return Atom.MailToPerson
            case MetadataProperty.RetireIn:
                return Atom.DaysString
            case _:
                return Atom.String
            
    @property
    def kv_label(self) -> str:
        match self:
            case MetadataProperty.StartDate | MetadataProperty.EndDate:
                return self.name.replace("Date", " Date")
            case _:
                return self.name
            


class FactProperty(Enum):
    Hostname = auto()
    Os = auto()
    Packages = auto()
    PackagesNames = auto()
    MemoryTotal = auto()
    MemoryUsage = auto()
    LocalStorageTotal = auto()
    LocalStorageUsage = auto()
    IsVirtual = auto()
    UptimeDays = auto()

    def extract(self, host_state: HostState):
        try:
            match self:
                case FactProperty.Hostname:
                    return host_state.facts.hostnamectl.hostname
                case FactProperty.Os:
                    return host_state.facts.hostnamectl.os
                case FactProperty.Packages:
                    return host_state.facts.packages
                case FactProperty.PackagesNames:
                    return [p.name for p in host_state.facts.packages]
                case FactProperty.MemoryTotal:
                    return host_state.facts.memory.total_mb
                case FactProperty.MemoryUsage:
                    return host_state.facts.memory.used_mb
                case FactProperty.LocalStorageTotal:
                    return host_state.facts.blocks[0].size_mb
                case FactProperty.LocalStorageUsage:
                    return host_state.facts.blocks[0].used_mb
                case FactProperty.IsVirtual:
                    return host_state.facts.hostnamectl.virtualization == "vmware"
                case FactProperty.UptimeDays:
                    return host_state.facts.uptime.days
                case _:
                    return None
        except AttributeError as e:
            raise PropertyReadError(f"The {self.name} property could not be accessed from the facts. Make sure the fact is being queried") from e
            
    @property
    def kv_label(self) -> str:
        return self.name
    
    @property
    def kv_atom(self) -> Atom:
        match self:
            case FactProperty.MemoryTotal | FactProperty.MemoryUsage | FactProperty.LocalStorageTotal | FactProperty.LocalStorageUsage:
                return Atom.MegaBytesString
            case FactProperty.UptimeDays:
                return Atom.DaysString
            case FactProperty.Packages:
                return Atom.InlineListPackages
            case _: return Atom.String