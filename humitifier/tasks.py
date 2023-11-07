from rocketry import Rocketry
from humitifier.infra import update_fact_db
from humitifier.config import CONFIG


def create_scheduler():
    task_app = Rocketry(execution="async")

    @task_app.task(CONFIG.tasks["infra_update"])
    async def infra_update():
        print("Updating facts")
        await update_fact_db()
        print("Fact Update Complete")

    return task_app
