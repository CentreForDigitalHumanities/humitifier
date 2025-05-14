#!/bin/bash

# Migrate the database, if automigrate is enabled
if [[ "$DJANGO_ENABLE_AUTOMIGRATE" != "0" && "$DJANGO_ENABLE_AUTOMIGRATE" != "false" && "$DJANGO_ENABLE_AUTOMIGRATE" != "False" ]]; then
    bash ./run_in_venv.sh python src/manage.py migrate
fi

# Collect static files if whitenoise is enabled
if [[ "$DJANGO_ENABLE_WHITENOISE" != "0" && "$DJANGO_ENABLE_WHITENOISE" != "false" && "$DJANGO_ENABLE_WHITENOISE" != "False" ]]; then
    bash ./run_in_venv.sh python src/manage.py collectstatic --noinput
fi

# Run da server
exec bash ./run_in_venv.sh gunicorn humitifier_server.wsgi:application -c gunicorn.conf.py "$@"
