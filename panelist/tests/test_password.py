# -- STDLIB
import re
from unittest.mock import patch
from urllib import parse

# -- DJANGO
from django.core import mail
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

# -- QXSMS
from hq.factories import HqFactory
from manager.factories import ManagerFactory
from panelist.factories import PanelistFactory


class PasswordUpdateTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.nc = ManagerFactory()
        cls.panelist = PanelistFactory()
        cls.hq = HqFactory()

    def test_hq_password_update(self):
        self.client.login(username=self.hq.email, password='hq')
        password_modified = {'old_password': 'hq', 'new_password1': 'Azerty1234!', 'new_password2': 'Azerty1234!'}
        self.client.post(reverse('password-change'), password_modified)
        self.assertTrue(self.client.login(username=self.hq.email, password='Azerty1234!'))

    def test_nc_password_update(self):
        self.client.login(username=self.nc.email, password='nc')
        password_modified = {'old_password': 'nc', 'new_password1': 'Azerty1234!', 'new_password2': 'Azerty1234!'}
        self.client.post(reverse('password-change'), password_modified)
        self.assertTrue(self.client.login(username=self.nc.email, password='Azerty1234!'))

    def test_pm_password_update(self):
        self.client.login(username=self.panelist.email, password='pm')
        password_modified = {'old_password': 'pm', 'new_password1': 'Azerty1234!', 'new_password2': 'Azerty1234!'}
        self.client.post(reverse('password-change'), password_modified)
        self.assertTrue(self.client.login(username=self.panelist.email, password='Azerty1234!'))


class PasswordResetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.nc = ManagerFactory()
        cls.panelist = PanelistFactory()
        cls.hq = HqFactory()

    def test_password_reset_panelist(self):
        """ Simulate password reset workflow

        Related notebook: 'Extracting token and uid from email'
        """
        # Mailbox starts empty
        self.assertFalse(mail.outbox)

        # Request to reset password.
        self.client.post(reverse('password-reset'), data={'email': self.panelist.email})

        # We received an email
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body

        capture_url = resolve_url('password-reset-confirm', uidb64=r'(?P<uid>\w+)', token=r'(?P<tok>[\w-]+)')
        match = re.search(parse.unquote(capture_url), body, re.MULTILINE)
        self.assertTrue(match)
        (uidb64, token) = match.group('uid', 'tok')

        new_pwd = 'Azerty1234!'
        # First visit the link, which plants a cookie with the token
        self.client.get(resolve_url('password-reset-confirm', token=token, uidb64=uidb64))
        response = self.client.post(
            reverse('password-reset-confirm', kwargs={'token': 'set-password', 'uidb64': uidb64}),
            {'new_password1': new_pwd, 'new_password2': new_pwd},
            follow=True
        )
        self.assertRedirects(response, reverse('panelist:home'), fetch_redirect_response=False)
        self.assertTrue(self.client.login(email=self.panelist.email, password=new_pwd))

    @patch("qxauth.forms.send_single_sms_distribution")
    def test_password_reset_panelist_by_phone(self, send_single_sms_distribution):
        """Simulate password reset workflow"""
        self.panelist.phone = '+33198765432'
        self.panelist.save()
        # Request to reset password.
        self.client.post(f"{reverse('password-reset')}?phone", data={'email_0': '+33', 'email_1': '198765432'})

        # A SMS has been sent
        send_single_sms_distribution.assert_called()
        kwargs = send_single_sms_distribution.call_args[1]
        message = kwargs.get('message')

        capture_url = resolve_url('password-reset-confirm', uidb64=r'(?P<uid>\w+)', token=r'(?P<tok>[\w-]+)')
        match = re.search(parse.unquote(capture_url), message, re.MULTILINE)
        self.assertTrue(match)
        (uidb64, token) = match.group('uid', 'tok')

        new_pwd = 'Azerty1234!'
        # First visit the link, which plants a cookie with the token
        self.client.get(resolve_url('password-reset-confirm', token=token, uidb64=uidb64))
        response = self.client.post(
            reverse('password-reset-confirm', kwargs={'token': 'set-password', 'uidb64': uidb64}),
            {'new_password1': new_pwd, 'new_password2': new_pwd},
            follow=True
        )
        self.assertRedirects(response, reverse('panelist:home'), fetch_redirect_response=False)
        self.assertTrue(self.client.login(email=self.panelist.email, password=new_pwd))
