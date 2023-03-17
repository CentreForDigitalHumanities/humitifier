import aiosql
import sqlite3
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from humitifier.models import Server


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
db = aiosql.from_path("db", "sqlite3")


with sqlite3.connect(".scribble/local.db") as conn:
    conn.row_factory = sqlite3.Row
    servers = db.queries.get_all_servers(conn)
servers = (Server.from_sql_row(row) for row in servers)
servers = {s.name: s for s in servers}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "user-grid.jinja", {"request": request, "servers": servers.values(), "title": "All backoffice servers"}
    )


@app.get("/htmx-server-details/{server_name}")
def reload_server_details(request: Request, server_name: str):
    return templates.TemplateResponse(
        "htmx/server-details.jinja", {"request": request, "server": servers[server_name]}
    )
