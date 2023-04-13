from humitifier.infra import facts
from pydantic import BaseModel
from typing import Type


class FactPing(BaseModel):
    users: list[facts.User] | None
    groups: list[facts.Group] | None
    hostnamectl: facts.HostnameCtl | None
    memory: facts.Memory | None
    block: list[facts.Block] | None
    uptime: facts.Uptime | None
    packages: list[facts.Package] | None
