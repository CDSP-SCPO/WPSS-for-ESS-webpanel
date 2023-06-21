# -- STDLIB
from unittest.mock import patch

# -- DJANGO
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

# -- QXSMS
from distributions.factories import (
    LinkDistributionFactory, MessageDistributionFactory,
)
from distributions.forms import (
    LinkDistributionGenerateForm, MessageDistributionSendForm,
)
from distributions.models import MessageDistribution
from hq.factories import HqFactory
from manager.factories import ManagerFactory
from panelist.factories import PanelistFactory


class MessageDistributionSendFormTestCase(TestCase):

    @patch('distributions.models.MessageDistribution')
    def test_empty_panel(self, msgd):

        msgd.get_candidates_stats.return_value = {'contact_mode': 0, 'fallback_mode': 0, 'total': 0}

        form = MessageDistributionSendForm(instance=msgd, history=[], data={'send_date':  timezone.now()})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['__all__'], ['The Panel must have at least one eligible contact'])

    @patch('distributions.models.MessageDistribution')
    def test_not_empty_panel_but_empty_target(self, msgd):
        msgd.get_candidates_stats.return_value = {'contact_mode': 10, 'fallback_mode': 0, 'total': 10}
        msgd.has_fallback = True
        form = MessageDistributionSendForm(instance=msgd, history=[], data={'send_date':  timezone.now()})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['__all__'], ['The Panel must have at least one eligible contact with fallback'])


class LinkDistributionGenerateFormTestCase(TestCase):

    @patch('distributions.models.LinkDistribution')
    def test_empty_panel(self, dist):
        dist.count_candidates = 0
        expiration_date = timezone.now() + timezone.timedelta(days=30)
        form = LinkDistributionGenerateForm(instance=dist, data={'expiration_date': expiration_date})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['__all__'], ['All panels are empty, there are no links to generate.'])


class MessageDistributionDescriptionTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.hq = HqFactory()
        cls.manager = ManagerFactory()
        cls.pm = PanelistFactory(panel__managers=[cls.manager])
        cls.link_distribution = LinkDistributionFactory(panels=[cls.pm.panel], create_links=True)
        cls.message_distribution = MessageDistributionFactory(
            link_distribution=cls.link_distribution,
            links=cls.link_distribution.links.all(),
            contact_mode=MessageDistribution.MODE_SMS,
            description='previous description')

    def setUp(self):
        self.client.login(username=self.hq.email, password='hq')

    def test_is_description(self):
        response = self.client.get(reverse('hq:msg-distribution-detail', kwargs={'pk': self.message_distribution.id}))
        self.assertContains(response, 'description')
        self.assertContains(response, self.message_distribution.description)

    def test_update_description(self):
        update = 'new description'
        url = reverse('hq:msg-distribution-update', kwargs={'pk': self.message_distribution.id})
        self.client.post(url, {
            'description': update,
        }, follow=True)
        self.message_distribution.refresh_from_db()
        self.assertEqual(self.message_distribution.description, update)
