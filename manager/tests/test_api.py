# -- STDLIB
from unittest.mock import patch

# -- DJANGO
from django.http import Http404
from django.test import TestCase

# -- QXSMS
from manager.api import get_task_info
from manager.factories import GroupTaskImportFactory, ManagerFactory
from panelist.factories import PanelistFactory


class APICeleryTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.manager = ManagerFactory()
        cls.panelist = PanelistFactory(panel__managers=[cls.manager])
        cls.task_import = GroupTaskImportFactory(panel=cls.panelist.panel)

    def test_get_task_info_task_doesnotexist(self):
        self.assertRaises(Http404, get_task_info, self.panelist.panel.pk, 123456)

    @patch('celery.result.AsyncResult.get')
    @patch('celery.result.AsyncResult.ready')
    def test_task_is_ready(self, ready, get):
        ready.return_value = True
        get.return_value = [{'new': 10, 'update': 0, 'delete': 0, 'skip': 0, 'error': 0, 'invalid': 0}, {}, False]
        task_info = get_task_info(self.panelist.panel.pk, self.task_import.pk)
        self.task_import.refresh_from_db()
        self.assertTrue(self.task_import.success)
        self.assertEqual(task_info,
                         {'results': {'new': 10, 'update': 0, 'delete': 0, 'skip': 0, 'error': 0, 'invalid': 0},
                          'errors': {},
                          'completed': True,
                          'dry_run': False})
