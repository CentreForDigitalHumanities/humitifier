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

# Eh, so, yeah... Only the scanner has a public one right now; the server actually
# chains everything internally so the scanner doesn't need to know what the server does.
SCANNER_RUN_SCAN = f"{SCANNER_QUEUE_PREFIX}.public.run_scan"
