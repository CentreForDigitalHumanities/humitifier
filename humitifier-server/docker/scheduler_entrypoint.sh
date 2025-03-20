#!/bin/bash

# Activate our venv
source /app/.venv/bin/activate

# Set default log level to INFO if not provided via the environment variable
LOG_LEVEL=${LOG_LEVEL:-INFO}

# Run da scheduler
exec python -m celery -A humitifier_server beat -l "$LOG_LEVEL"
