import uvicorn
import asyncio
from humitifier.app import create_base_app
from humitifier.fake.gen.host import FakeHost
from humitifier.fake.gen.factping import FakeFactPing

from humitifier.models.host_state import HostState
from humitifier.config import AppConfig

from rocketry import Rocketry

host_pool = FakeHost.create_pool()
hosts = [next(host_pool) for _ in range(100)]
states = [HostState(host=h, facts=FakeFactPing.generate()) for h in hosts]


cfg = AppConfig.default(hosts=hosts)
app = create_base_app(cfg)
app.state.host_states_kv = {s.host.fqdn: s for s in states}


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