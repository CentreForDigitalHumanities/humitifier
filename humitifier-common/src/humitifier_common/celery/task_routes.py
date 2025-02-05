from .task_names import SERVER_QUEUE_PREFIX, SCANNER_QUEUE_PREFIX


task_routes = {
    f"{SCANNER_QUEUE_PREFIX}.*": {"queue": "scanner"},
    f"{SERVER_QUEUE_PREFIX}.*": {"queue": "default"},
}
