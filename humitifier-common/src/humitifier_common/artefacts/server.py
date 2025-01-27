"""
A collection of facts that only make sense to collect on a server.
"""

from pydantic import BaseModel

from humitifier_common.artefacts.registry import fact, metric


##
## Server metadata
##


class VHost(BaseModel):
    docroot: str
    servername: str
    serveraliases: list[str] | None = None


@fact(group="server")
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


@metric(group="server")
class Uptime(float):
    pass


##
## Puppet
##


@fact(group="server")
class PuppetAgent(BaseModel):
    enabled: bool
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


@fact(group="server")
class IsWordpress(BaseModel):
    is_wp: bool
