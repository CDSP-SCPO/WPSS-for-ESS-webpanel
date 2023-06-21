# Ensures Celery app loaded when Django start
# and used by shared_task

# -- QXSMS (LOCAL)
from .celery import app as celery_app

__all__ = ['celery_app']
