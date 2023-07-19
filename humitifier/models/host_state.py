from pydantic import BaseModel
from humitifier.models.host import Host
from humitifier.models.factping import FactPing


class HostState(BaseModel):
    host: Host
    facts: FactPing