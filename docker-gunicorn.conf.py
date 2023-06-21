# -- STDLIB
import os

# -- THIRDPARTY
import gunicorn

gunicorn.SERVER_SOFTWARE = 'gunicorn'

bind = "0.0.0.0:8000"
workers = 4
timeout = 180

for k, v in os.environ.items():
    if k.startswith("GUNICORN_"):
        key = k.split('_', 1)[1].lower()
        locals()[key] = v
