#!/bin/bash

# Migrate the database
bash ./run_in_venv.sh python src/manage.py migrate

# Run da server
exec bash ./run_in_venv.sh gunicorn humitifier_server.wsgi:application -c gunicorn.conf.py "$@"
