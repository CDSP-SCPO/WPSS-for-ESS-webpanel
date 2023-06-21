# -- STDLIB
import os

# -- THIRDPARTY
from celery import Celery

# Used by celery CLI tool
# Must come before app instance creation
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qxsms.settings')

# Instance of the Celery library
app = Celery('qxsms')

# Add Django settings module as configuration source
app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover tasks defined in applications' tasks.py modules
# Avoids manually adding them via CELERY_IMPORTS
app.autodiscover_tasks()

if __name__ == '__main__':
    worker = app.Worker()
    worker.start()
