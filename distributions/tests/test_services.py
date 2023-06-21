# -- DJANGO
from django.test import TestCase

# -- QXSMS (LOCAL)
from ..services import history_links_stats, msg_distributions_stats


class ServicesTestCase(TestCase):

    def test_history_links_stats(self):
        links_history = [
            {
                'panel': 'pp',
                'panel_pk': 1,
                'status': 'HardBounce',
                'finished': False,
                'started': False,
                'failed': True
             },
            {
                'panel': 'pp',
                'panel_pk': 1,
                'status': 'Opened',
                'finished': False,
                'started': False,
                'failed': False
             },

            {
                'panel': 'test',
                'panel_pk': 2,
                'status': 'Blocked',
                'finished': False,
                'started': False,
                'failed': True

             },
            {
                'panel': 'test',
                'panel_pk': 2,
                'status': 'Blocked',
                'finished': False,
                'started': False,
                'failed': True

            },
            {
                'panel': 'test',
                'panel_pk': 2,
                'status': 'Blocked',
                'finished': False,
                'started': False,
                'failed': True
            },
            {
                'panel': 'test',
                'panel_pk': 2,
                'status': 'Blocked',
                'finished': False,
                'started': False,
                'failed': True
            },

            {
                'panel': 'test',
                'panel_pk': 2,
                'status': 'SurveyFinished',
                'finished': True,
                'started': False,
                'failed': False
            },
            {
                'panel': 'test',
                'panel_pk': 2,
                'status': 'SurveyFinished',
                'finished': True,
                'started': False,
                'failed': False
            },

            {
                'panel': 'test',
                'panel_pk': 2,
                'status': 'SurveyStarted',
                'finished': False,
                'started': True,
                'failed': False
            },

            {
                'panel': 'test',
                'panel_pk': 2,
                'status': 'Pending',
                'finished': False,
                'started': False,
                'failed': False,
                'not_started': True
            },

        ]

        stats = history_links_stats(links_history)
        self.assertEqual(stats['Total']['total'], 10)
        self.assertEqual(len(stats), 3)
        self.assertEqual(stats['test']['failed'], 4)
        self.assertEqual(stats['test']['finished'], 2)
        self.assertEqual(stats['test']['not_started'], 1)
        self.assertEqual(stats['test']['total'], 8)

        msgdist_stats = msg_distributions_stats(links_history)
        self.assertEqual(msgdist_stats['Total']['total'], 10)
        self.assertEqual(len(msgdist_stats), 3)
        self.assertEqual(msgdist_stats['pp']['hard_bounced'], 1)
        self.assertEqual(msgdist_stats['pp']['opened'], 1)
        self.assertEqual(msgdist_stats['pp']['total'], 2)
