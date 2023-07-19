from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from humitifier.config import AppConfig
from humitifier.filters import Filter
from humitifier.infra.utils import init_client, collect_facts, parse_facts
from humitifier.views.components.host_grid import HostGrid
from humitifier.views.components.host_modal import HostModal
from humitifier.views.pages.index import HostGridIndex
from humitifier.views.utils import Wrapper


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    host_grid = HostGridIndex.create(
        host_states=list(request.app.state.host_states_kv.values()),
        app_config=request.app.state.config
    )
    return HTMLResponse(
            Wrapper.Base.render(html_content=host_grid.html)
        )


@router.get("/hx-host-modal/{fqdn}")
async def host_details(request: Request, fqdn: str):
    host_state = request.app.state.host_states_kv[fqdn]
    target = "innerHTML:#hx-modal"
    modal = HostModal.create(
        host_state=host_state,
        metadata_properties=request.app.state.config.metadata_properties,
        fact_properties=request.app.state.config.fact_properties
    )
    return HTMLResponse(
        Wrapper.HxOobSwap.render(html_content=modal.html, target=target)
    )


@router.get("/hx-filter-hosts")
async def filter_hosts(request: Request):
    filter_kv = {k: v for k, v in request.query_params.items() if v}
    host_states = list(request.app.state.host_states_kv.values())
    filtered_hosts = Filter.apply_from_kv(host_states, filter_kv)
    hostgrid = HostGrid.create(host_states=filtered_hosts, grid_properties=request.app.state.config.grid_properties)
    return HTMLResponse(
        Wrapper.HxOobSwap.render(html_content=hostgrid.inner_html, target="innerHTML:.grid")
    )



@router.get("/hx-clear-host-modal")
async def clear_target(request: Request):
    return HTMLResponse(
        Wrapper.HxOobSwap.render(html_content="", target="innerHTML:#hx-modal")
    )


# def create_app(config: AppConfig) -> FastAPI:
#     app = FastAPI()
#     app.mount("/static", StaticFiles(directory="static"), name="static")
#     app.state.config = config
#     app.state.pssh_client = init_client(config)
#     outputs = collect_facts(app.state.pssh_client, config)
#     fact_kv = parse_facts(outputs, config)
#     app.state.hosts = [(host, fact_kv[host]) for host in config.hosts]
#     app.include_router(router)
#     return app
