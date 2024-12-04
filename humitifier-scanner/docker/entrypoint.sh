#!/bin/bash

# Activate our venv
source /app/.venv/bin/activate

# CD into the app directory
cd /app/src/ || exit 1

# Run celery worker
exec python -m celery -A humitifier_scanner.celery_worker worker -Q scanner -l INFO -n scanner@%h