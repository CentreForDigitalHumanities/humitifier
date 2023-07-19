import uvicorn
import asyncio
from humitifier.app import AppConfig,  router
from humitifier.fake.gen.host import FakeHost
from humitifier.fake.gen.factping import FakeFactPing

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from humitifier.models.host_state import HostState
from humitifier.config import AppConfig
from humitifier.filters import Filter
from humitifier.properties import MetadataProperty, FactProperty
from rocketry import Rocketry

host_pool = FakeHost.create_pool()
hosts = [next(host_pool) for _ in range(100)]
states = [HostState(host=h, facts=FakeFactPing.generate()) for h in hosts]



app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.state.config = AppConfig(
    hosts=hosts,
    rules=[],
    filters=[
        Filter.Hostname,
        Filter.Os,
        Filter.Department,
        Filter.Owner,
        Filter.Purpose,
        Filter.Person,
        Filter.Package
    ],
    metadata_properties=[
        MetadataProperty.Department,
        MetadataProperty.Owner,
        MetadataProperty.Purpose,
        MetadataProperty.StartDate,
        MetadataProperty.EndDate,
        MetadataProperty.RetireIn,
        MetadataProperty.People

    ],
    fact_properties=[
        FactProperty.Hostname,
        FactProperty.Os,
        FactProperty.IsVirtual,
        FactProperty.UptimeDays,
        FactProperty.Packages
    ],
    grid_properties=[
        MetadataProperty.Department,
        FactProperty.Os,
        FactProperty.UptimeDays
    ],
    pssh_conf={},
    poll_interval="every 5 seconds",
    environment="demo"
)
app.state.host_states_kv = {s.host.fqdn: s for s in states}
app.include_router(router)




task_app = Rocketry(execution="async")

@task_app.task('every 15 seconds')
def do_stuff():
    app.state.host_states_kv = {h.fqdn: HostState(host=h, facts=FakeFactPing.generate()) for h in hosts}


class Server(uvicorn.Server):
    """Customized uvicorn.Server

    Uvicorn server overrides signals and we need to include
    Rocketry to the signals."""
    def handle_exit(self, sig: int, frame) -> None:
        task_app.session.shut_down()
        return super().handle_exit(sig, frame)


async def main():
    "Run scheduler and the API"
    server = Server(config=uvicorn.Config(app, workers=1, loop="asyncio", host="0.0.0.0", port=8000))

    dash = asyncio.create_task(server.serve())
    sched = asyncio.create_task(task_app.serve())

    await asyncio.wait([sched, dash])

if __name__ == "__main__":
    asyncio.run(main())