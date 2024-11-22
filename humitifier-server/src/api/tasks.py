from celery import shared_task


@shared_task(name="server.api.clear_expired_tokens")
def clear_expired_tokens():
    from oauth2_provider.models import clear_expired

    clear_expired()
