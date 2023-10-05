import uvicorn
import asyncio
from humitifier.facts import HostnameCtl, Blocks, Groups, Memory, PackageList, Uptime, Users
from humitifier.config import HostConfig, AppConfig, FiltersetConfig, FactConfig
from humitifier.state.app import AppState

from humitifier.props import (
    Fqdn,
    Department,
    Hostname,
    LocalStorage,
    MemoryUse,
    Os,
    PackageList,
    Virtualization,
)
from humitifier.config.host_view import HostViewConfig
from humitifier.app import router, FastAPI, StaticFiles
from humitifier.html import SelectInput, SearchInput

DEFAULT_VIEW = HostViewConfig(
    card=[Hostname, Department, LocalStorage, MemoryUse],
    table=[Hostname, Os, Department, LocalStorage, MemoryUse, Virtualization, PackageList],
)


config = AppConfig(
    hosts=[
        HostConfig(
            fqdn=Fqdn("gw-c-dh-static.im.hum.uu.nl"),
            metadata=[],
            view_cfg=DEFAULT_VIEW,
        ),
        HostConfig(
            fqdn=Fqdn("gw-d11-fsw-davinci-acc.im.hum.uu.nl"),
            metadata=[],
            view_cfg=DEFAULT_VIEW,
        ),
    ],
    facts=FactConfig(
        {
            HostnameCtl,
            Blocks,
            Groups,
            Memory,
            PackageList,
            Uptime,
            Users,
        }
    ),
    filters=FiltersetConfig(
        [(Department, SelectInput), (Hostname, SearchInput), (Os, SelectInput), (PackageList, SearchInput)]
    ),
    pssh_conf={
        "user": "donatas",
        "proxy_host": "cratylus.im.hum.uu.nl",
    },
    poll_interval="every 10 minutes",
)


state = AppState.initialize(config)
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.state.app_state = state
app.include_router(router)


class Server(uvicorn.Server):
    """Customized uvicorn.Server

    Uvicorn server overrides signals and we need to include
    Rocketry to the signals."""

    # def handle_exit(self, sig: int, frame) -> None:
    #     task_app.session.shut_down()
    #     return super().handle_exit(sig, frame)


async def main():
    "Run scheduler and the API"
    server = Server(config=uvicorn.Config(app, workers=1, loop="asyncio", host="0.0.0.0", port=8000))

    dash = asyncio.create_task(server.serve())
    # sched = asyncio.create_task(task_app.serve())

    await asyncio.wait([dash])


if __name__ == "__main__":
    asyncio.run(main())
