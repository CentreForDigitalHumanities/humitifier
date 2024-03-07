import uvicorn
import asyncio
from humitifier.dashboard import app as dashboard
from humitifier.tasks import app as task_app
from humitifier.logging import logging


class Server(uvicorn.Server):
    """Customized uvicorn.Server

    Uvicorn server overrides signals and we need to include
    Rocketry to the signals."""

    def handle_exit(self, sig: int, frame) -> None:
        task_app.session.shut_down()
        return super().handle_exit(sig, frame)


async def main():
    "Run scheduler and the API"
    logging.info("Starting scheduler and API")
    server = Server(config=uvicorn.Config(dashboard, workers=1, loop="asyncio", host="0.0.0.0", port=8000))

    dash = asyncio.create_task(server.serve())
    sched = asyncio.create_task(task_app.serve())

    await asyncio.wait([dash, sched])


if __name__ == "__main__":
    asyncio.run(main())
