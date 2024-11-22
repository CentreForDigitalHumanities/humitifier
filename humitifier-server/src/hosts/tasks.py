from celery import shared_task


@shared_task(name="server.hosts.historical_clean")
def historical_clean_task():
    from .utils import historical_clean

    historical_clean()
