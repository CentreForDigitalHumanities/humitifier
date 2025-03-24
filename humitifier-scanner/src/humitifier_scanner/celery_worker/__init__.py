from .config import app as celery_app
from .tasks import *

__all__ = ("celery_app",)
