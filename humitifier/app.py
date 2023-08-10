from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from humitifier.state.app import AppState, HostCollectionState
from humitifier.html import HostGrid, Page, FilterSet, HxSwap, HostModal, HtmlString, HostGridItems
from humitifier.urls import Url



router = APIRouter()

def _get_state(request: Request) -> AppState:
    return request.app.state.app_state


@router.get(Url.Index.value, response_class=HTMLResponse)
async def index(request: Request):
    state = _get_state(request)
    if request.headers.get("HX-Request"):
        all_hosts = state.host_collection.values()
        hosts = state.filterset.apply(
            {k:v for k, v in request.query_params.items() if v},
            all_hosts
        )
        collection = HostCollectionState({h.fqdn: h for h in hosts})
        swap = HxSwap(component=collection.component(HostGridItems), target="innerHTML:.grid")
        return HTMLResponse(swap.render())
    page = Page([
        state.filterset.component(FilterSet),
        state.host_collection.component(HostGrid)
    ])
    return HTMLResponse(page.render())


@router.get(Url.HostDetails.value)
async def host_details(request: Request, fqdn: str):
    state = _get_state(request)
    host_state = state.host_collection[fqdn]
    target = "innerHTML:#hx-modal"
    modal = host_state.component(HostModal)
    swap = HxSwap(component=modal, target=target)
    return HTMLResponse(swap.render())



@router.get(Url.CloseModal.value)
async def clear_target(request: Request):
    swap = HxSwap(component=HtmlString(""), target="innerHTML:#hx-modal")
    return HTMLResponse(swap.render())


def create_base_app() -> FastAPI:
    app = FastAPI()
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(router)
    return app

