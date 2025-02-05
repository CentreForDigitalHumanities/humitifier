from celery import shared_task

from humitifier_server.celery.task_names import API_CLEAR_EXPIRED_TOKENS


@shared_task(name=API_CLEAR_EXPIRED_TOKENS)
def clear_expired_tokens():
    from oauth2_provider.models import clear_expired

    clear_expired()
