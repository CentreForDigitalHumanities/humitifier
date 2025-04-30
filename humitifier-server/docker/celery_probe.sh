#!/bin/bash

# Activate our venv
source /app/.venv/bin/activate

# Run the probe
exec python -m celery -A humitifier_server inspect ping -d celery@$HOSTNAME
