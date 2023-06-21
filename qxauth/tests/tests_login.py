# -- DJANGO
from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import TestCase
from django.urls import reverse

# -- QXSMS
from hq.factories import HqFactory
from manager.factories import ManagerFactory
from panelist.factories import PanelistFactory

User = get_user_model()


class LoginTestCase(TestCase):
    """Test the main login view.

    Check that it properly redirects depending on the user's group membership.
    """

    @classmethod
    def setUpTestData(cls):
        cls.hq = HqFactory()
        cls.manager = ManagerFactory()
        cls.pm = PanelistFactory(panel__managers=[cls.manager])
        User.objects.create_superuser(email='admin@qxsms.org', password='admin')
        User.objects.create_user(email='user@qxsms.org', password='user')

    # Note: in the following tests, we still pass "username" because it is what is expected in the AuthenticateForm.
    # The function authenticate() (overriden in qxauth/backends.py) uses this value to login the user
    # with the appropriate field *email or phone*
    def test_login_failure(self):
        r = self.client.post('', data={'username': self.hq.email, 'password': 'wrong'})
        self.assertFalse(r.context['user'].is_authenticated)

    def test_admin_login_success(self):
        r = self.client.post('', data={'username': 'admin@qxsms.org', 'password': 'admin'})
        self.assertRedirects(r, reverse('admin:index'))

    def test_hq_login_success(self):
        r = self.client.post('', data={'username': self.hq.email, 'password': 'hq'})
        self.assertRedirects(r, reverse('hq:home'))

    def test_hq_login_success_with_redirect(self):
        r = self.client.post('/?next=/hq/', data={'username': self.hq.email, 'password': 'hq'})
        self.assertRedirects(r, reverse('hq:home'))

    def test_nc_login_success(self):
        r = self.client.post('', data={'username': self.manager.email, 'password': 'nc'})
        # manager:home redirects to manager:panel-list
        self.assertRedirects(r, reverse('manager:home'), target_status_code=302)

    def test_pm_login_success(self):
        r = self.client.post('', data={'username': self.pm.email, 'password': 'pm'})
        self.assertRedirects(r, reverse('panelist:home'))

    def test_login_with_phone(self):
        phone = str(self.pm.phone)
        prefix = phone[0:3]
        number = phone[3:]
        r = self.client.post('?phone', data={'username_0': prefix, 'username_1': number, 'password': 'pm'})
        self.assertIn(SESSION_KEY, self.client.session)
        self.assertRedirects(r, reverse('panelist:home'))

    def test_nogrpuser_login_permission_denied(self):
        r = self.client.post('', data={'username': 'user@qxsms.org', 'password': 'user'})
        self.assertEqual(r.status_code, 403)
