from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from humitifier.fake.models import generate_server

from typing import Optional

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

servers = (generate_server() for _ in range(100))
servers = {s.name: s for s in servers}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "user-grid.jinja",
        {
            "request": request,
            "servers": servers.values(),
            "title": "All backoffice servers",
            "display_count": len(servers),
            "critical_count": len([s for s in servers.values() if s.status == "critical"]),
            "list_filters": {
                "hostname": [s for s in servers],
                "os": set([s.os for s in servers.values()]),
                "department": set([s.requesting_department for s in servers.values()]),
                "server_type": set([s.server_type for s in servers.values()]),
            },
        },
    )


@app.get("/htmx-server-details/{server_name}")
def reload_server_details(request: Request, server_name: str):
    return templates.TemplateResponse(
        "htmx/server-details.jinja", {"request": request, "server": servers[server_name]}
    )


@app.get("/htmx-filter-grid-by")
def filter_server_grid(
    request: Request,
    hostname: Optional[str] = None,
    os: Optional[str] = None,
    department: Optional[str] = None,
    server_type: Optional[str] = None,
):
    filtered = servers.values()
    if hostname:
        filtered = [f for f in filtered if hostname in f.name]
    if os:
        filtered = [f for f in filtered if os == f.os]
    if department:
        filtered = [f for f in filtered if department in f.requesting_department]
    if server_type:
        filtered = [f for f in filtered if server_type in f.server_type]
    return templates.TemplateResponse(
        "htmx/filtered-server-grid.jinja",
        {
            "request": request,
            "servers": filtered,
            "title": "Filtered view",
            "display_count": len(filtered),
            "critical_count": len([s for s in filtered if s.status == "critical"]),
        },
    )
