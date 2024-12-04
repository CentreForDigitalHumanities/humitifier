import os

from celery import Celery

from humitifier_agent.config import CONFIG

if not CONFIG.celery:
    raise ValueError("Celery config is not set in the config")

if not CONFIG.celery.rabbit_mq_url:
    raise ValueError("RabbitMQ URL is not set in the config")

# TODO: custom config file
broker = os.environ.get("CELERY_BROKER_URL", default="amqp://guest@localhost//")

app = Celery(
    "humitifier_agent",
    broker=None,
    # broker=broker,
    # broker_connection_retry_on_startup=True,
)

app.conf.task_routes = {
    "agent.*": {"queue": "agent"},
    "server.*": {"queue": "default"},
}
