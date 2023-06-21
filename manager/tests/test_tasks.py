# -- STDLIB
from collections import OrderedDict
from unittest.mock import patch

# -- DJANGO
from django.test import TestCase

# -- THIRDPARTY
import import_export.results
import tablib
from celery.result import AsyncResult

# -- QXSMS
from manager import tasks
from manager.factories import ManagerFactory
from manager.models import GroupTaskImport
from panelist.factories import PanelistFactory


class ContactTasksTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.nc = ManagerFactory()
        cls.panelist = PanelistFactory(panel__managers=[cls.nc])
        cls.headers = ['idno', 'sex', 'email', 'cntry', 'netusoft', 'eduyrs', 'dybrn', 'mthbrn', 'yrbrn', 'lng']
        cls.rows = [(str(cls.panelist.ess_id), '9', 'cid_new@qxsms.com', 'SK', '9', '0', '10', '8', '1970', 'FR'),
                    (str(cls.panelist.ess_id + 1),
                     '9', 'cid_0448852@qxsms.com', 'HR', '9', '3', '1', '8', '1984', 'EN'), ]
        cls.group_task = GroupTaskImport.objects.create(
            celery_group_id=1,
            file_name='TEST',
            dry_run=True,
            panel=cls.panelist.panel)

    def test_import_contact(self):
        return_value = (OrderedDict(
            [('new', 1), ('update', 1), ('delete', 0), ('skip', 0), ('error', 0), ('invalid', 0)]),
            {},
            False)

        self.assertEqual(
            tasks.task_import_data_celery(self.panelist.panel.pk, self.rows, self.headers, dry_run=True),
            return_value)

        tasks.task_import_data_celery(self.panelist.panel.pk, self.rows, self.headers, dry_run=True)
        self.rows.append(('3', '9', 'ERROR', 'RO', '9', '2', '6', '6', '1974', 'EN'))
        return_value = (OrderedDict(
            [('new', 1), ('update', 1), ('delete', 0), ('skip', 0), ('error', 0), ('invalid', 1)]),
            {3: {'email': ['Enter a valid email address.']}},
            True)
        self.assertEqual(
            tasks.task_import_data_celery(self.panelist.panel.pk, self.rows, self.headers, dry_run=True),
            return_value)

    @patch('manager.tasks.task_import_data_celery.delay')
    def test_import_data_celery(self, delay):
        delay.return_value = AsyncResult(id='test')
        dataset = tablib.Dataset(*self.rows, headers=self.headers)
        nb = GroupTaskImport.objects.count()
        tasks.import_data_celery(self.headers, dataset, self.panelist.panel.pk, 'test_file_name')
        self.assertEqual(GroupTaskImport.objects.count(), nb+1)

    @patch('manager.tasks.task_import_data_celery.delay')
    def test_import_data_celery_nodryrun(self, delay):
        nb = GroupTaskImport.objects.count()
        delay.return_value = AsyncResult(id='parent')
        tasks.import_data_celery(self.headers, self.rows, self.panelist.panel.pk, 'test_file_name', dry_run=False)
        self.assertEqual(GroupTaskImport.objects.count(), nb + 1)

    @patch('import_export.results.Result.has_validation_errors')
    @patch('utils.csvimport.ProfileResource.import_data')
    def test_import_data_called_twice(self, import_data, has_validation_errors):
        # Test that import_data() is called twice when dry_run is set to False without validation_error
        import_data.return_value = import_export.results.Result()
        has_validation_errors.return_value = False
        dataset = tablib.Dataset(*self.rows, headers=self.headers)
        tasks.task_import_data_celery(self.panelist.panel.pk, dataset, self.headers, False)
        self.assertEqual(import_data.call_count, 2)
