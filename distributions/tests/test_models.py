# -- STDLIB
from unittest import TestCase, skip

# -- QXSMS
from distributions import models as m


class ContactModeTestCase(TestCase):

    def test_has_finished(self):
        record = {'status': 'SurveyFinished'}
        self.assertTrue(m.has_finished(record))

    def test_has_not_finished(self):
        record = {'status': 'SurveyStarted'}
        self.assertFalse(m.has_finished(record))

    def test_has_started(self):
        record = {'status': 'SurveyStarted'}
        self.assertTrue(m.has_started(record))

    def test_filter_for_completion_status(self):
        history = [
            {'contactId': 1, 'status': 'SurveyStarted'},
            {'contactId': 2, 'status': 'SurveyFinished'},
            {'contactId': 3, 'status': 'Pending'},
        ]
        res = m._filter_completion_status(history, m.MessageDistribution.TARGET_ALL)
        self.assertSetEqual(res, {1, 2, 3})
        res = m._filter_completion_status(history, m.MessageDistribution.TARGET_NOT_FINISHED)
        self.assertSetEqual(res, {1, 3})
        res = m._filter_completion_status(history, m.MessageDistribution.TARGET_FINISHED)
        self.assertSetEqual(res, {2})


class MessageDistributionTestCase(TestCase):

    @skip("Not implemented")
    def test_get_candidates_stats(self):
        pass
