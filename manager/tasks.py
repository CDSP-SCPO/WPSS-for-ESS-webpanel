# -- THIRDPARTY
import tablib
from celery import shared_task
from celery.utils.log import get_task_logger

# -- QXSMS
from utils.csvimport import ProfileResource

# -- QXSMS (LOCAL)
from .models import GroupTaskImport

logger = get_task_logger(__name__)


def import_data_celery(headers, dataset, panel_pk, filename,
                       dry_run=True) -> GroupTaskImport:

    gt_import = GroupTaskImport.objects.create(file_name=filename,
                                               dry_run=dry_run, panel_id=panel_pk)

    result = task_import_data_celery.delay(panel_pk, dataset, headers, dry_run)
    gt_import.celery_group_id = result.id
    gt_import.save()
    return gt_import


@shared_task(bind=True)
def task_import_data_celery(self, panel_pk, dataset, headers, dry_run):

    resource = ProfileResource(panel_id=panel_pk)
    ds = tablib.Dataset(*dataset, headers=headers)
    res = resource.import_data(ds, dry_run=True)

    validation_error = {}

    if res.has_validation_errors():
        for line in res.invalid_rows:
            validation_error[line.number] = {}
            validation_error[line.number].update(line.error_dict)

    elif not dry_run:
        res = resource.import_data(ds, dry_run=False)

    return (res.totals, validation_error, res.has_errors() or res.has_validation_errors())
