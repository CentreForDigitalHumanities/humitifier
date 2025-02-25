from celery import shared_task

from hosts.utils import historical_clean
from humitifier_server.celery.task_names import *


@shared_task(name=HOSTS_HISTORICAL_CLEAN)
def historical_clean_task():
    historical_clean()
