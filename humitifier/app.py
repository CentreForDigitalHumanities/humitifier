from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from humitifier.fake.models import generate_server
from humitifier.views.filter import ServerFilter
from typing import Optional

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="web")

servers = (generate_server() for _ in range(100))
servers = {s.name: s for s in servers}


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    server_list = list(servers.values())
    filters = ServerFilter(servers=server_list)
    return templates.TemplateResponse(
        "pages/simple-grid.jinja",
        {"request": request, "servers": server_list, "filters": filters},
    )


@app.get("/hx-server-details/{server_name}")
def reload_server_details(request: Request, server_name: str):
    return templates.TemplateResponse(
        "hx/simple-grid-details.jinja", {"request": request, "server": servers[server_name]}
    )


@app.get("/hx-filter-interactive-server-grid")
def filter_server_grid(
    request: Request,
    hostname: Optional[str] = None,
    username: Optional[str] = None,
    package: Optional[str] = None,
    owner: Optional[str] = None,
    contact: Optional[str] = None,
    purpose: Optional[str] = None,
    os: Optional[str] = None,
    department: Optional[str] = None,
) -> HTMLResponse:
    filtered = servers.values()
    if hostname:
        filtered = (f for f in filtered if hostname in f.name)
    if username:
        filtered = (f for f in filtered if username in f.users)
    if package:
        filtered = (f for f in filtered if package in f.packages)
    if owner:
        filtered = (f for f in filtered if owner in f.service_contract.owner.name)
    if contact:
        filtered = (f for f in filtered if contact in f.service_contract.people)
    if purpose:
        filtered = (f for f in filtered if purpose in f.service_contract.purpose)
    if os:
        filtered = (f for f in filtered if os in f.os)
    if department:
        filtered = (f for f in filtered if department in f.service_contract.entity)
    filtered = list(filtered)
    return templates.TemplateResponse("hx/simple-grid-filtered.jinja", {"request": request, "servers": filtered})


@app.get("/hx-clear/{target}")
def clear_target(request: Request, target: str):
    return templates.TemplateResponse("hx/clear.jinja", {"request": request, "target": target})


# @app.get("/", response_class=HTMLResponse)
# def index(request: Request):
#     return templates.TemplateResponse(
#         "user-grid.jinja",
#         {
#             "request": request,
#             "servers": servers.values(),
#             "title": "All backoffice servers",
#             "display_count": len(servers),
#             "critical_count": len([s for s in servers.values() if s.status == "critical"]),
#             "list_filters": {
#                 "hostname": [s for s in servers],
#                 "os": set([s.os for s in servers.values()]),
#                 "department": set([s.requesting_department for s in servers.values()]),
#                 "server_type": set([s.server_type for s in servers.values()]),
#             },
#         },
#     )


# @app.get("/htmx-server-details/{server_name}")
# def reload_server_details(request: Request, server_name: str):
#     return templates.TemplateResponse(
#         "htmx/server-details.jinja", {"request": request, "server": servers[server_name]}
#     )


# @app.get("/htmx-filter-grid-by")
# def filter_server_grid(
#     request: Request,
#     hostname: Optional[str] = None,
#     os: Optional[str] = None,
#     department: Optional[str] = None,
#     server_type: Optional[str] = None,
# ):
#     filtered = servers.values()
#     if hostname:
#         filtered = [f for f in filtered if hostname in f.name]
#     if os:
#         filtered = [f for f in filtered if os == f.os]
#     if department:
#         filtered = [f for f in filtered if department in f.requesting_department]
#     if server_type:
#         filtered = [f for f in filtered if server_type in f.server_type]
#     return templates.TemplateResponse(
#         "htmx/filtered-server-grid.jinja",
#         {
#             "request": request,
#             "servers": filtered,
#             "title": "Filtered view",
#             "display_count": len(filtered),
#             "critical_count": len([s for s in filtered if s.status == "critical"]),
#         },
#     )
