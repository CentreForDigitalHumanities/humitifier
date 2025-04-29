from celery import Celery, signals
import sentry_sdk
from sentry_sdk import HttpTransport

from humitifier_common.celery.task_routes import task_routes
from humitifier_scanner.config import CONFIG
from humitifier_scanner.constants import HUMITIFIER_VERSION

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
app.conf.timezone = "Europe/Amsterdam"


@signals.celeryd_init.connect
def init_sentry(**_kwargs):
    if CONFIG.celery.sentry_dsn:

        class CustomHttpTransport(HttpTransport):
            def _get_pool_options(self):
                # This should never be used in production, or even on any server
                # THis is ONLY for when you're (for some reason) running sentry locally!
                options = super()._get_pool_options()
                if CONFIG.celery.sentry_insecure_cert:
                    options["cert_reqs"] = "CERT_NONE"

                return options

        sentry_sdk.init(
            dsn=CONFIG.celery.sentry_dsn,
            send_default_pii=True,
            traces_sample_rate=1.0,
            transport=CustomHttpTransport,
            release=HUMITIFIER_VERSION,
        )
