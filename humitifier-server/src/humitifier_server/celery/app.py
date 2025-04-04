import os

from celery import Celery
from django.conf import settings  # noqa
from humitifier_common.celery.task_routes import task_routes


# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "humitifier_server.settings")

app = Celery("humitifier_server")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.task_routes = task_routes
