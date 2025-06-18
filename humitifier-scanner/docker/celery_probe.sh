#!/bin/bash

# Activate our venv
source /app/.venv/bin/activate

# CD into the app directory
cd /app/src/ || exit 1

# Run the probe
exec python -m celery -A humitifier_scanner.celery_worker inspect ping -d scanner@$HOSTNAME
