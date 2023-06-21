# -- STDLIB
from unittest import skip

# -- DJANGO
from django.test import TestCase
from django.urls import reverse

# -- QXSMS
from hq.factories import HqFactory
from manager.factories import ManagerFactory
from panelist.factories import PanelistFactory
from qxauth.models import User
from qxauth.tokens import phone_token_generator


class LoginViewTestCase(TestCase):

    def test_login_view(self):
        response = self.client.get(reverse('login'))
        # Only one field for the username
        self.assertContains(response, "id=\"id_username\"")

    def test_phone_login_view(self):
        response = self.client.get(f"{reverse('login')}?phone")
        # There are two fields displayed (phone country code + phone number)
        self.assertContains(response, "id=\"id_username_0\"")
        self.assertContains(response, "id=\"id_username_1\"")


class PhonePasswordResetTestCase(TestCase):

    @skip('Sending single SMS needs to be reviewed')
    def test_sms_password_reset_panelist(self):
        """ Simulate password reset workflow with sms """
        pass


class PasswordChangeTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.hq = HqFactory()
        cls.manager = ManagerFactory()
        cls.pm = PanelistFactory(panel__managers=[cls.manager])

    def test_correct_template_rendered(self):
        url = reverse('password-change')
        self.client.login(email=self.hq.email, password='hq')
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'hq/password_change.html')
        self.client.login(email=self.manager.email, password='nc')
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'manager/password_change.html')
        self.client.login(email=self.pm.email, password='pm')
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'panelist/password_change.html')

    def test_password_change(self):
        url = reverse('password-change')
        self.client.login(email=self.hq.email, password='hq')
        response = self.client.post(
            url,
            {'old_password': 'hq', 'new_password1': 'password1', 'new_password2': 'password1'}
        )
        self.assertRedirects(response, reverse('hq:home'))


class TokenGeneratorTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.pm = PanelistFactory()

    def test_phone_token_generator(self):
        user = User.objects.get(email=self.pm.email)
        base_token = phone_token_generator.make_token(user)
        user.phone = "+33612345678"
        new_token = phone_token_generator.make_token(user)
        self.assertNotEqual(base_token, new_token)
