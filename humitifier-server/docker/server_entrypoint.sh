#!/bin/bash

# Migrate the database
./run_in_venv.sh python src/manage.py migrate

# Run da server
exec ./run_in_venv.sh gunicorn humitifier_server.wsgi:application -c gunicorn.conf.py "$@"
