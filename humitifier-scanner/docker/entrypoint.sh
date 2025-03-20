#!/bin/bash

# Activate our venv
source /app/.venv/bin/activate

# CD into the app directory
cd /app/src/ || exit 1

# Set default log level to INFO if not provided via the environment variable
LOG_LEVEL=${LOG_LEVEL:-INFO}

# Run celery worker
exec python -m celery -A humitifier_scanner.celery_worker worker -Q scanner -l "$LOG_LEVEL" -n scanner@%h
