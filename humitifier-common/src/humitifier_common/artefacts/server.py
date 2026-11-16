"""
A collection of facts that only make sense to collect on a server.
"""

from datetime import datetime
from ipaddress import IPv4Address
from typing import Literal, TypedDict

from humitifier_common.artefacts import ArtefactMetadata
from pydantic import BaseModel, Field

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


@metric(group=SERVER, name="Uptime", max_version=2)
class Uptime(float):
    pass


@metric(group=SERVER, name="Uptime", min_version=3)
class V3Uptime(BaseModel):
    uptime: float
    since: datetime


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


##
## Docker
##


class DockerContainer(BaseModel):
    container_id: str
    command: str | None = None
    created_at: datetime | None = None
    health_status: str | None = None
    running_for: str | None = None  # president?
    size_str: str | None = None
    size_bytes: int | None = None
    state: str | None = None
    status: str | None = None

    image_str: str | None = None
    image_name: str | None = None
    image_tag: str | None = None

    labels: dict[str, str] = Field(default_factory=dict)

    mounts: list[str] | None = None
    names: list[str] | None = None
    networks: list[str] | None = None
    exposed_ports: list[str] | None = None

    platform_arch: str | None = None
    platform_os: str | None = None


class DockerImage(BaseModel):
    image_id: str
    digest: str | None = None

    size_str: str | None = None
    size_bytes: int | None = None

    created_at: datetime | None = None
    created_since: str | None = None

    used_by_n_containers: int | None = None

    repository: str | None = None
    tag: str | None = None


class DockerComposeProject(BaseModel):
    name: str
    status_str: str | None = None
    status: str | None = None
    running_containers: int | None = None
    exited_containers: int | None = None
    paused_containers: int | None = None
    restarting_containers: int | None = None
    created_containers: int | None = None
    dead_containers: int | None = None
    config_files: list[str] | None = Field(default_factory=list)


@fact(group=SERVER, metadata=ArtefactMetadata(null_is_valid=True), min_version=3)
class Docker(BaseModel):
    containers: list[DockerContainer] = Field(default_factory=list)
    images: list[DockerImage] = Field(default_factory=list)
    compose_projects: list[DockerComposeProject] = Field(default_factory=list)
