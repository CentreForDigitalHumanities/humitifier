from celery import shared_task

from humitifier_server.celery.task_names import MAIN_LOG_ERROR
from humitifier_server.logger import logger


@shared_task(name=MAIN_LOG_ERROR)
def log_error(*args):
    """
    Logs errors encountered during a task execution. This function is intended
    as an generic error handler, if no specific handler is available.

    :param args: Variable length argument list containing details or messages
        regarding the error to be logged.

    :return: None
    """
    logger.error(f"Error during task: %s", args)
