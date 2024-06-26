import asyncpg
import json
import os
from dataclasses import dataclass
from typing import Callable, Literal
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from humitifier.alerts import ALERTS
from humitifier.config import CONFIG
from humitifier.models import Host, get_hosts
from humitifier.logging import logging

import sentry_sdk

logger = logging.getLogger(__name__)

if sentry_dsn := os.getenv("SENTRY_DSN"):
    logging.info("Sentry enabled")
    sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=1.0, profiles_sample_rate=1.0)


template_env = Environment(loader=FileSystemLoader("humitifier/templates"))
template_env.filters["json"] = lambda x: json.dumps(x, indent=4, sort_keys=True, separators=(",", ": "))
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@dataclass
class Filter:
    typ: Literal["search", "select", "hidden"]
    id: str
    label: str
    options: set[str]
    value: str | None
    fn: Callable[[Host], bool]


def host_filters(request: Request | None, all_hosts: list[Host]) -> list[Filter]:

    return [
        Filter(
            typ="search",
            id="fqdn",
            label="Search Hosts",
            options={str(h.fqdn) for h in all_hosts},
            value=request.query_params.get("fqdn") if request else None,
            fn=lambda h, p: not p.get("fqdn") or p.get("fqdn") in h.fqdn,
        ),
        Filter(
            typ="select",
            id="os",
            label="Operating System",
            options={str(h.os) for h in all_hosts},
            value=request.query_params.get("os") if request else None,
            fn=lambda h, p: not p.get("os") or p.get("os") == h.os,
        ),
        Filter(
            typ="select",
            id="alert",
            label="Alert",
            options={a.__name__ for a in ALERTS},
            value=request.query_params.get("alert") if request else None,
            fn=lambda h, p: not p.get("alert") or p.get("alert") in h.alert_codes,
        ),
        Filter(
            typ="select",
            id="department",
            label="Department",
            options={str(h.department) for h in all_hosts},
            value=request.query_params.get("department") if request else None,
            fn=lambda h, p: not p.get("department") or p.get("department") == h.department,
        ),
        Filter(
            typ="select",
            id="contact",
            label="Contact",
            options={str(h.contact) for h in all_hosts},
            value=request.query_params.get("contact") if request else None,
            fn=lambda h, p: not p.get("contact") or p.get("contact") == h.contact,
        ),
        Filter(
            typ="search",
            id="package",
            label="Package",
            options={pkg.name for h in all_hosts for pkg in h.packages or []},
            value=request.query_params.get("package") if request else None,
            fn=lambda h, p: not p.get("package") or p.get("package") in {pkg.name for pkg in h.packages},
        ),
        Filter(
            typ="hidden",
            id="severity",
            label="Severity",
            options={"info", "warning", "critical"},
            value=request.query_params.get("severity") if request else None,
            fn=lambda h, p: not p.get("severity") or p.get("severity") == h.severity,
        ),
        Filter(
            typ="select",
            label="Is Wordpress",
            id="is_wp",
            options={"true", "false"},
            value=request.query_params.get("is_wp") if request else None,
            fn=lambda h, p: not p.get("is_wp") or p.get("is_wp") == str(h.is_wp).lower(),
        ),
    ]


def _current_hosts(request: Request, all_hosts: list[Host]) -> list[Host]:
    filters = host_filters(request, all_hosts)
    return [h for h in all_hosts if all(f.fn(h, request.query_params) for f in filters)]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not {k: v for k, v in request.query_params.items() if v} and os.path.exists("static/index_prerender.html"):
        with open("static/index_prerender.html") as f:
            return HTMLResponse(f.read())
    hosts = await get_hosts()
    current_hosts = _current_hosts(request, hosts)
    filters = host_filters(request, hosts)
    template = template_env.get_template("page_index.jinja2")
    return HTMLResponse(
        template.render(
            current_hosts=current_hosts,
            critical_count=len([h for h in current_hosts if h.severity == "critical"]),
            warning_count=len([h for h in current_hosts if h.severity == "warning"]),
            info_count=len([h for h in current_hosts if h.severity == "info"]),
            filters=filters,
        )
    )


@app.on_event("startup")
async def run_migrations():
    logger.info("Applying migrations...")
    conn = await asyncpg.connect(CONFIG.db)
    for f in os.listdir(CONFIG.migrations_dir):
        logger.info(f"Applying {f}")
        with open(f"{CONFIG.migrations_dir}/{f}") as sql_file:
            await conn.execute(sql_file.read())
