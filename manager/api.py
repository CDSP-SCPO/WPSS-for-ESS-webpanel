# -- STDLIB
from collections import Counter
from typing import TypedDict

# -- DJANGO
from django.shortcuts import get_object_or_404

# -- THIRDPARTY
from celery.result import AsyncResult

# -- QXSMS
from manager.models import GroupTaskImport


class TaskInfo(TypedDict):
    results: Counter
    errors: dict
    completed: bool
    dry_run: bool


def get_task_info(panel_pk, task_import_id) -> TaskInfo:

    task_import = get_object_or_404(GroupTaskImport, id=task_import_id, panel__pk=panel_pk)

    return _get_task_info(task_import)


def _get_task_info(task_import) -> TaskInfo:

    task = AsyncResult(task_import.celery_group_id)

    completed = False
    result = Counter()
    validation_error = {}

    if task.ready():
        result, validation_error, b = task.get()
        completed = not b
        if completed:
            task_import.success = True
            task_import.save()

    return {"results": result, "errors": validation_error, "completed": completed, "dry_run": task_import.dry_run}
