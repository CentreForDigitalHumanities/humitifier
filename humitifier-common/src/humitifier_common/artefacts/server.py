"""
A collection of facts that only make sense to collect on a server.
"""

from ipaddress import IPv4Address
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


##
## Webserver
##


class WebhostProxy(BaseModel):
    type: str
    endpoint: str
    options: dict[str, str] | None = None


class WebhostRewriteRule(TypedDict):
    conditions: list[str]
    rule: str


class WebhostAuthRequire(TypedDict):
    type: str
    negation: bool
    values: list[str]


class WebhostAuth(TypedDict):
    type: str
    provider: str | None
    requires: list[WebhostAuthRequire]


class WebhostLocation(TypedDict):
    document_root: str | None
    auth: WebhostAuth | None
    proxy: WebhostProxy | None
    rewrite_rules: list[WebhostRewriteRule] | None


class Webhost(BaseModel):
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
## DNS
##


class DNSLookup(BaseModel):
    name: str
    a_records: list[IPv4Address]
    cname_records: list[str]


@fact(group=SERVER)
class DNS(BaseModel):
    dns_lookups: list[DNSLookup] | None = None
    reverse_dns_lookups: dict[IPv4Address, list[str]] | None = None


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
