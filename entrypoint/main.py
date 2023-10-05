import uvicorn
import asyncio
from user_config import app  # noqa
from humitifier.tasks import create_scheduler


task_app = create_scheduler(app)


# class Server(uvicorn.Server):
#     """Customized uvicorn.Server

#     Uvicorn server overrides signals and we need to include
#     Rocketry to the signals."""
#     def handle_exit(self, sig: int, frame) -> None:
#         task_app.session.shut_down()
#         return super().handle_exit(sig, frame)


async def main():
    "Run scheduler and the API"
    server = uvicorn.Server(config=uvicorn.Config(app, workers=1, loop="asyncio", host="0.0.0.0", port=8000))

    dash = asyncio.create_task(server.serve())
    # sched = asyncio.create_task(task_app.serve())

    await asyncio.wait(
        [
            # sched,
            dash
        ]
    )


if __name__ == "__main__":
    asyncio.run(main())
