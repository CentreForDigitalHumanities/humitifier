#!/bin/bash

# Migrate the database, if automigrate is enabled
if [[ "$HUMITIFIER_SERVER_DJANGO__ENABLE_AUTOMIGRATE" != "0" && "$HUMITIFIER_SERVER_DJANGO__ENABLE_AUTOMIGRATE" != "false" && "$HUMITIFIER_SERVER_DJANGO__ENABLE_AUTOMIGRATE" != "False" ]]; then
    bash ./run_in_venv.sh python src/manage.py migrate
fi

# Collect static files if whitenoise is enabled
if [[ "$HUMITIFIER_SERVER_STATIC_FILES__ENABLE_WHITENOISE" != "0" && "$HUMITIFIER_SERVER_STATIC_FILES__ENABLE_WHITENOISE" != "false" && "$HUMITIFIER_SERVER_STATIC_FILES__ENABLE_WHITENOISE" != "False" ]]; then
    bash ./run_in_venv.sh python src/manage.py collectstatic --noinput
fi

# Run da server
exec bash ./run_in_venv.sh gunicorn humitifier_server.wsgi:application -c gunicorn.conf.py "$@"
