from enum import Enum
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from humitifier.infra import retrieve_host_data, Host
from humitifier.infra.alerts import ALERTS


template_env = Environment(loader=FileSystemLoader("humitifier/dash/templates"))


class Url(Enum):
    InfraIndex = "/"


router = APIRouter()


class InfraIndexCtx(list[Host]):
    @property
    def host_count(self):
        return len(self)

    @property
    def critical_count(self):
        return len([h for h in self if h.alert_severity == "critical"])

    @property
    def warn_count(self):
        return len([h for h in self if h.alert_severity == "warning"])

    @property
    def alert_count(self):
        return sum([h.alert_count for h in self])


class InfraFilterCtx(list[Host]):
    def filter(self, query_params) -> "InfraIndexCtx":
        hosts = self
        if hostname := query_params.get("fqdn"):
            hosts = [h for h in hosts if hostname.lower() in h.fqdn]
        if os := query_params.get("os"):
            hosts = [h for h in hosts if h.facts.os == os]
        if alert := query_params.get("alert"):
            hosts = [h for h in hosts if alert in [a for a in h.alert_codes]]
        if department := query_params.get("department"):
            hosts = [h for h in hosts if h.department == department]
        if contact := query_params.get("contact"):
            hosts = [h for h in hosts if h.contact[0] == contact]
        if package := query_params.get("package"):
            hosts = [h for h in hosts if any([package in pkgname for pkgname in h.package_names or []])]
        if severity := query_params.get("severity"):
            hosts = [h for h in hosts if h.alert_severity == severity]
        return InfraIndexCtx(hosts)

    @property
    def fqdn_options(self) -> list[str]:
        return sorted(list({h.fqdn for h in self}))

    @property
    def os_options(self) -> list[str]:
        return sorted(list({h.facts.os for h in self if h.facts.os}))

    @property
    def alerts_options(self) -> list[str]:
        return sorted(list({a.__name__ for a in ALERTS}))

    @property
    def contacts_options(self) -> list[str]:
        return sorted(list({h.contact[0] for h in self if h.contact}))

    @property
    def department_options(self) -> list[str]:
        return sorted(list({h.department for h in self if h.department}))

    @property
    def package_options(self) -> list[str]:
        return sorted(list({p for h in self for p in h.package_names or []}))


@router.get(Url.InfraIndex.value, response_class=HTMLResponse)
async def infra_index(request: Request):
    hosts = await retrieve_host_data()
    filter_ctx = InfraFilterCtx(hosts)
    hosts_ctx = filter_ctx.filter(request.query_params)
    template = template_env.get_template("infra_index.jinja2")
    return HTMLResponse(template.render(hosts=hosts_ctx, filters=filter_ctx, params=request.query_params))
