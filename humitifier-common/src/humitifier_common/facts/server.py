"""
A collection of facts that only make sense to collect on a server.
"""

from dataclasses import dataclass

from humitifier_common.facts import fact


##
## Server metadata
##


@fact(namespace="server")
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


@fact(namespace="server")
class Uptime(float):
    pass


##
## Puppet
##


@fact(namespace="server")
@dataclass
class PuppetAgent:
    enabled: bool
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


@fact(namespace="server")
@dataclass
class IsWordpress:
    is_wp: bool
