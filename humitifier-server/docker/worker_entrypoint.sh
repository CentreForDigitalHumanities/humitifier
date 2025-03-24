#!/bin/bash

# Activate our venv
source /app/.venv/bin/activate

# Set default log level to INFO if not provided via the environment variable
LOG_LEVEL=${LOG_LEVEL:-INFO}

# Run da worker
exec python -m celery -A humitifier_server worker -Q default -l "$LOG_LEVEL"
