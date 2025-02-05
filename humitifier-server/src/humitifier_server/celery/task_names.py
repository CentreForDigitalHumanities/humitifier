from humitifier_common.celery.task_names import SERVER_QUEUE_PREFIX

API_CLEAR_EXPIRED_TOKENS = f"{SERVER_QUEUE_PREFIX}.internal.api.clear_expired_tokens"

HOSTS_HISTORICAL_CLEAN = f"{SERVER_QUEUE_PREFIX}.internal.hosts.historical_clean"
HOSTS_START_SCAN = f"{SERVER_QUEUE_PREFIX}.internal.hosts.start_scan"
HOSTS_PROCESS_SCAN = f"{SERVER_QUEUE_PREFIX}.internal.hosts.process_scan"
HOSTS_SCAN_HANDLE_ERROR = f"{SERVER_QUEUE_PREFIX}.internal.hosts.handle_scan_error"
