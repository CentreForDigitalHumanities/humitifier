from humitifier_common.celery.task_names import SERVER_QUEUE_PREFIX

API_CLEAR_EXPIRED_TOKENS = f"{SERVER_QUEUE_PREFIX}.internal.api.clear_expired_tokens"

MAIN_LOG_ERROR = f"{SERVER_QUEUE_PREFIX}.internal.main.log_error"

HOSTS_HISTORICAL_CLEAN = f"{SERVER_QUEUE_PREFIX}.internal.hosts.historical_clean"

SCANNING_GET_SCAN_INPUT = f"{SERVER_QUEUE_PREFIX}.internal.scanning.get_scan_input"
SCANNING_RUN_SCAN = f"{SERVER_QUEUE_PREFIX}.internal.scanning.run_scan"
SCANNING_SAVE_SCAN = f"{SERVER_QUEUE_PREFIX}.internal.scanning.save_scan"
SCANNING_SCAN_HANDLE_ERROR = (
    f"{SERVER_QUEUE_PREFIX}.internal.scanning.handle_scan_error"
)
SCANNING_FULL_SCAN_SCHEDULER = (
    f"{SERVER_QUEUE_PREFIX}.internal.scanning.schedule_full_scans"
)
