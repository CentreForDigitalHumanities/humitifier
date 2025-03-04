from humitifier_common.celery.task_names import SERVER_QUEUE_PREFIX

API_CLEAR_EXPIRED_TOKENS = f"{SERVER_QUEUE_PREFIX}.internal.api.clear_expired_tokens"

HOSTS_HISTORICAL_CLEAN = f"{SERVER_QUEUE_PREFIX}.internal.hosts.historical_clean"

SCANNING_START_FULL_SCAN = f"{SERVER_QUEUE_PREFIX}.internal.scanning.start_full_scan"
SCANNING_PROCESS_SCAN = f"{SERVER_QUEUE_PREFIX}.internal.scanning.process_scan"
SCANNING_SCAN_HANDLE_ERROR = (
    f"{SERVER_QUEUE_PREFIX}.internal.scanning.handle_scan_error"
)
SCANNING_FULL_SCAN_SCHEDULER = (
    f"{SERVER_QUEUE_PREFIX}.internal.scanning.schedule_full_scans"
)
