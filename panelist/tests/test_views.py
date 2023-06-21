# -- DJANGO
from django.shortcuts import resolve_url
from django.test import TestCase

# -- QXSMS
from manager.factories import ManagerFactory
from panelist.factories import PanelistFactory


class PanelistViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = ManagerFactory()
        cls.panelist = PanelistFactory(panel__managers=[cls.manager])
        cls.panel = cls.panelist.panel
        cls.panelist.user.set_password('pm')
        cls.panelist.user.save()

    def setUp(self):
        self.client.login(username=self.panelist.email, password='pm')

    def test_incentive_context(self):
        self.panel.incentive_amount = "5€"
        self.panel.save()
        response = self.client.get(resolve_url('panelist:help'))
        self.assertTrue('incentive_amount' in response.context)

    def test_help_context(self):
        self.panel.contact_info = "HELP YOURSELF"
        self.panel.save()
        response = self.client.get(resolve_url('panelist:help'))
        self.assertFalse('manager' in response.context)
        self.assertTrue('contact_info' in response.context)

    def test_help_context_fallback(self):
        self.panel.contact_info = None
        self.panel.save()
        response = self.client.get(resolve_url('panelist:help'))
        self.assertTrue('manager' in response.context)
        self.assertFalse('contact_info' in response.context)


class PhoneChangeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        manager = ManagerFactory()
        cls.panelist = PanelistFactory(panel__managers=[manager])

    def setUp(self):
        self.client.login(username=self.panelist.email, password='pm')

    def test_phone_change_view(self):
        response = self.client.get(resolve_url('panelist:phone-change'))
        self.assertTrue(response.context["user"].email == self.panelist.email)


class UpdatePanelistTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        manager = ManagerFactory()
        cls.pm = PanelistFactory(panel__managers=[manager])

    def setUp(self):
        self.client.login(username=self.pm.email, password='pm')

    def test_access_profile_update_view(self):
        response = self.client.get(resolve_url('panelist:profile-update'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'], self.pm)
