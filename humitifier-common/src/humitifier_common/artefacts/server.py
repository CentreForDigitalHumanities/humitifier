"""
A collection of facts that only make sense to collect on a server.
"""

from pydantic import BaseModel

from humitifier_common.artefacts.groups import SERVER
from humitifier_common.artefacts.registry import fact, metric


##
## Server metadata
##


class VHost(BaseModel):
    docroot: str
    servername: str
    serveraliases: list[str] | None = None


@fact(group=SERVER)
class HostMeta(BaseModel):
    department: str | None = None
    contact: str | None = None
    update_policy: dict[str, bool] | None = None
    webdav: str | None = None
    vhosts: list[dict[str, VHost]] | None = None
    fileservers: list[str] | None = None
    databases: dict[str, list[str]] | None = None


##
## Uptime
##


@metric(group=SERVER)
class Uptime(float):
    pass


##
## Puppet
##


@fact(group=SERVER)
class PuppetAgent(BaseModel):
    enabled: bool
    running: bool | None
    disabled_message: str | None = None
    code_roles: list[str] | None = None
    profiles: list[str] | None = None
    environment: str | None = None
    data_role: str | None = None
    data_role_variant: str | None = None
    last_run: str | None = None
    is_failing: bool | None = None


##
## Wordpress
##


@fact(group=SERVER)
class IsWordpress(BaseModel):
    is_wp: bool


##
## Reboot Policy
##


@fact(group=SERVER)
class RebootPolicy(BaseModel):
    configured: bool
    enabled: bool | None = None
    cron_minute: str | None = None
    cron_hour: str | None = None
    cron_monthday: str | None = None
