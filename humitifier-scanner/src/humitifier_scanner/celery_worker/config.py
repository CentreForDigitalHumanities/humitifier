from celery import Celery
from humitifier_common.celery.task_routes import task_routes


from humitifier_scanner.config import CONFIG

if not CONFIG.celery:
    raise ValueError("Celery config is not set in the config")

if not CONFIG.celery.rabbit_mq_url:
    raise ValueError("RabbitMQ URL is not set in the config")


app = Celery(
    "humitifier_scanner",
    broker=CONFIG.celery.rabbit_mq_url.unicode_string(),
    broker_connection_retry_on_startup=True,
)

app.conf.task_routes = task_routes
