import asyncpg
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

if sentry_dsn := os.getenv("SENTRY_DSN"):
    sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=1.0, profiles_sample_rate=1.0)

template_env = Environment(loader=FileSystemLoader("humitifier/templates"))
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@dataclass
class Filter:
    typ: Literal["search", "select"]
    id: str
    label: str
    options: set[str]
    value: str | None
    fn: Callable[[Host], bool]


def _host_filters(request: Request, all_hosts: list[Host]) -> list[Filter]:
    return [
        Filter(
            typ="search",
            id="fqdn",
            label="Search Hosts",
            options={h.fqdn for h in all_hosts},
            value=request.query_params.get("fqdn"),
            fn=lambda h, p: not p.get("fqdn") or p.get("fqdn") in h.fqdn,
        ),
        Filter(
            typ="select",
            id="os",
            label="Operating System",
            options={h.os for h in all_hosts},
            value=request.query_params.get("os"),
            fn=lambda h, p: not p.get("os") or p.get("os") == h.os,
        ),
        Filter(
            typ="select",
            id="alert",
            label="Alert",
            options={a.__name__ for a in ALERTS},
            value=request.query_params.get("alert"),
            fn=lambda h, p: not p.get("alert") or p.get("alert") in h.alert_codes,
        ),
        Filter(
            typ="select",
            id="department",
            label="Department",
            options={h.department for h in all_hosts},
            value=request.query_params.get("department"),
            fn=lambda h, p: not p.get("department") or p.get("department") == h.department,
        ),
        Filter(
            typ="select",
            id="contact",
            label="Contact",
            options={h.contact for h in all_hosts},
            value=request.query_params.get("contact"),
            fn=lambda h, p: not p.get("contact") or p.get("contact") == h.contact,
        ),
        Filter(
            typ="search",
            id="package",
            label="Package",
            options={pkg.name for h in all_hosts for pkg in h.packages or []},
            value=request.query_params.get("package"),
            fn=lambda h, p: not p.get("package") or p.get("package") in {pkg.name for pkg in h.packages},
        ),
    ]


def _current_hosts(request: Request, all_hosts: list[Host]) -> list[Host]:
    filters = _host_filters(request, all_hosts)
    return [h for h in all_hosts if all(f.fn(h, request.query_params) for f in filters)]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    hosts = await get_hosts()
    current_hosts = _current_hosts(request, hosts)
    filters = _host_filters(request, hosts)
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
    logging.info("Applying migrations...")
    conn = await asyncpg.connect(CONFIG.db)
    for f in os.listdir(CONFIG.migrations_dir):
        logging.info(f"Applying {f}")
        with open(f"{CONFIG.migrations_dir}/{f}") as sql_file:
            await conn.execute(sql_file.read())
