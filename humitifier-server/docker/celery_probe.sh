#!/bin/bash

# Run the probe
exec bash ./run_in_venv.sh python -m celery -A humitifier_server inspect ping -d celery@$HOSTNAME
