"""
A collection of facts that only make sense to collect on a server.
"""

from dataclasses import dataclass

from humitifier_common.facts.registry import fact, metric


##
## Server metadata
##


@fact(group="server")
@dataclass
class HostMeta:
    department: str | None = None
    contact: str | None = None
    update_policy: dict[str, bool] | None = None
    webdav: str | None = None
    vhosts: list[dict] | None = None  # TODO: figure out what dict fields are needed
    fileservers: list[str] | None = None
    databases: dict[dict[str, list[str]]] | None = None


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
@dataclass
class PuppetAgent:
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
@dataclass
class IsWordpress:
    is_wp: bool
