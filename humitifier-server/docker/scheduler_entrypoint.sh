#!/bin/bash

# Set default log level to INFO if not provided via the environment variable
LOG_LEVEL=${LOG_LEVEL:-INFO}

# Run da scheduler
exec ./run_in_venv.sh python -m celery -A humitifier_server beat -l "$LOG_LEVEL" --scheduler django_celery_beat.schedulers:DatabaseScheduler
