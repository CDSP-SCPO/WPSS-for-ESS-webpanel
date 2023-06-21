# -- DJANGO
from django.db import models

# -- QXSMS
from hq.models import Panel


class GroupTaskImport(models.Model):
    celery_group_id = models.CharField(max_length=100)
    file_name = models.CharField(max_length=100)
    dry_run = models.BooleanField()
    upload_date = models.DateTimeField(auto_now_add=True)
    panel = models.ForeignKey(Panel, on_delete=models.CASCADE, null=True)
    success = models.BooleanField(default=False)
