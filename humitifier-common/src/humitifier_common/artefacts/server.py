"""
A collection of facts that only make sense to collect on a server.
"""

from typing import Literal, TypedDict

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


class WebhostProxy(TypedDict):
    type: str
    endpoint: str


class WebhostRewriteRule(TypedDict):
    conditions: list[str]
    rule: str


class WebhostAuth(TypedDict):
    type: str
    provider: str | None


class WebhostLocation(TypedDict):
    document_root: str | None
    auth: WebhostAuth | None
    proxy: WebhostProxy | None
    rewrite_rules: list[WebhostRewriteRule] | None


class Webhost(TypedDict):
    listen_ports: list[int]
    webserver: Literal["apache", "nginx"]
    filename: str
    document_root: str
    hostname: str
    hostname_aliases: list[str]
    locations: dict[str, WebhostLocation]
    rewrite_rules: list[WebhostRewriteRule]
    includes: list[str]


@fact(group=SERVER)
class Webserver(BaseModel):
    hosts: list[Webhost]


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
