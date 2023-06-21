# -- DJANGO
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

# -- QXSMS
from hq.factories import HqFactory
from manager.factories import ManagerFactory
from panelist.factories import PanelistFactory

User = get_user_model()


class AuthorizationTestCase(TestCase):
    """Test middleware-based user authorization"""

    @classmethod
    def setUpTestData(cls):
        cls.hq = HqFactory()
        cls.manager = ManagerFactory()
        cls.pm = PanelistFactory(panel__managers=[cls.manager])
        User.objects.create_user(email='user@qxsms.org', password='user')

    def test_hq_permission_granted(self):
        self.client.login(username=self.hq.email, password='hq')
        r = self.client.get(reverse('hq:home'))
        self.assertEqual(r.status_code, 200)

    def test_hq_permission_denied(self):
        self.client.login(username=self.hq.email, password='hq')
        r = self.client.get(reverse('manager:home'))
        self.assertEqual(r.status_code, 403)
        r = self.client.get(reverse('panelist:home'))
        self.assertEqual(r.status_code, 403)

    def test_nc_permission_granted(self):
        self.client.login(username=self.manager.email, password='nc')
        r = self.client.get(reverse('manager:home'))
        # Since we only have panel-list view, it does not really make sense to have a home where we can only
        # go to this view, so it redirects to it instead
        self.assertEqual(r.status_code, 302)

    def test_nc_permission_denied(self):
        self.client.login(username=self.manager.email, password='nc')
        r = self.client.get(reverse('hq:home'))
        self.assertEqual(r.status_code, 403)
        r = self.client.get(reverse('panelist:home'))
        self.assertEqual(r.status_code, 403)

    def test_pm_permission_granted(self):
        self.client.login(username=self.pm.email, password='pm')
        r = self.client.get(reverse('panelist:home'))
        # The profile is enabled, so 200 should be expected rather than redirect
        self.assertEqual(r.status_code, 200)

    def test_pm_permission_denied(self):
        self.client.login(username=self.pm.email, password='pm')
        r = self.client.get(reverse('hq:home'))
        self.assertEqual(r.status_code, 403)
        r = self.client.get(reverse('manager:home'))
        self.assertEqual(r.status_code, 403)

    def test_nogrpuser_permission_denied(self):
        self.client.login(username='user@qxsms.org', password='user')
        r = self.client.get(reverse('hq:home'))
        self.assertEqual(r.status_code, 403)
        r = self.client.get(reverse('manager:home'))
        self.assertEqual(r.status_code, 403)
        r = self.client.get(reverse('panelist:home'))
        self.assertEqual(r.status_code, 403)
