import os

bind = "0.0.0.0:8000"
workers = 3
capture_output = True
# How verbose the Gunicorn error logs should be
loglevel = os.getenv("LOG_LEVEL", "WARNING")