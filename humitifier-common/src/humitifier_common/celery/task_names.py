"""
This file contains constants of Celery task names that all apps need to know about
(Basically, the 'API' between the server and scanner workers over Celery).

All tasks follow the same-ish format:

<worker_type>.<task_type>(.<component>).<task_name>

Where:
- worker_type: scanner or server; this controls the routing of the task, and is the
  only section that actually has runtime-meaning.
- task_type: Either public or internal; whether the task is available for cross-worker
  calling. (This file should only have public!)
- component: optionally an identifier of where in the codebase the tasks lives.
- task_name: the name of the actual task

(Note: for internal tasks, only worker_type is actually required, everything else can
be whatever. Just be nice and try to work with this system).
"""

SERVER_QUEUE_PREFIX = "server"
SCANNER_QUEUE_PREFIX = "scanner"
NETWORK_INDEXER_QUEUE_PREFIX = "network_indexer"

# Eh, so, yeah... Only basic start tasks are 'public knowledge'; the server actually
# chains everything internally so the other workers don't need to know what the server
# does.
SCANNER_RUN_SCAN = f"{SCANNER_QUEUE_PREFIX}.public.run_scan"
NETWORK_INDEXER_INDEX_IP = f"{NETWORK_INDEXER_QUEUE_PREFIX}.public.index_ip"
