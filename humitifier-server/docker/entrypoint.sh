#!/bin/bash

# Activate our venv
source /app/.venv/bin/activate

# Migrate the database
python src/manage.py migrate

# Run da server
exec gunicorn humitifier_server.wsgi:application -c gunicorn.conf.py "$@"