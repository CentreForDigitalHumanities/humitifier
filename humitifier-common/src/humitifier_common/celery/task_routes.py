from .task_names import SERVER_QUEUE_PREFIX, SCANNER_QUEUE_PREFIX, NETWORK_INDEXER_QUEUE_PREFIX


task_routes = {
    f"{SCANNER_QUEUE_PREFIX}.*": {"queue": "scanner"},
    f"{SERVER_QUEUE_PREFIX}.*": {"queue": "default"},
    f"{NETWORK_INDEXER_QUEUE_PREFIX}.*": {"queue": "network_indexer"},
    f"celery.*": {"queue": "default"},  # Needed for celery tasks to be scheduled
}
