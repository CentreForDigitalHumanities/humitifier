import asyncio
from humitifier.tasks import app as task_app
from humitifier.logging import logging



async def main():
    "Run scheduler"
    logging.info("Starting scheduler")

    sched = asyncio.create_task(task_app.serve())

    await asyncio.wait([sched])


if __name__ == "__main__":
    asyncio.run(main())
