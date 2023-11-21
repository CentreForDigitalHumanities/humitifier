from rocketry import Rocketry
from humitifier.infra import update_fact_db
from humitifier.config import CONFIG


def create_scheduler():
    task_app = Rocketry(execution="async")

    @task_app.task(CONFIG.tasks["infra_update"])
    async def infra_update():
        await update_fact_db()

    return task_app
