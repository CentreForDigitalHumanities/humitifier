from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from humitifier.models.server import Server
from humitifier.models.cluster import Cluster

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="web")

servers = Server.load("/data/packagescan.json", "/data/contracts")
cluster = Cluster(name="main", servers=servers)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    server_list = cluster.servers
    filters = cluster.opts(server_list)
    return templates.TemplateResponse(
        "pages/simple-grid.jinja",
        {"request": request, "servers": server_list, "filters": filters},
    )


@app.get("/hx-server-details/{server_name}")
async def reload_server_details(request: Request, server_name: str):
    server = cluster.get_server_by_hostname(server_name)
    return templates.TemplateResponse("hx/simple-grid-details.jinja", {"request": request, "server": server})


@app.get("/hx-server-issues/{server_name}")
async def get_server_issues(request: Request, server_name: str):
    server = cluster.get_server_by_hostname(server_name)
    return templates.TemplateResponse("hx/simple-grid-issues.jinja", {"request": request, "issues": server.issues})


@app.get("/hx-filter-interactive-server-grid")
async def filter_server_grid(
    request: Request,
    hostname: str | None = None,
    package: str | None = None,
    owner: str | None = None,
    contact: str | None = None,
    purpose: str | None = None,
    os: str | None = None,
    entity: str | None = None,
    issue: str | None = None,
) -> HTMLResponse:
    filter_args = {
        "hostname": hostname,
        "package": package,
        "owner": owner,
        "contact": contact,
        "purpose": purpose,
        "os": os,
        "entity": entity,
        "issue": issue,
    }
    filtered = cluster.apply_filters(**filter_args)
    return templates.TemplateResponse("hx/simple-grid-filtered.jinja", {"request": request, "servers": filtered})


@app.get("/hx-clear/{target}")
async def clear_target(request: Request, target: str):
    return templates.TemplateResponse("hx/clear.jinja", {"request": request, "target": target})
