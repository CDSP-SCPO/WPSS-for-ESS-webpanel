# -- STDLIB
import re
from unittest.mock import patch
from urllib import parse

# -- DJANGO
from django.contrib.auth import get_user_model
from django.core import mail
from django.http import HttpResponseNotFound
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode

# -- QXSMS
from manager.factories import ManagerFactory
from panelist.factories import PanelistFactory
from panelist.models import Profile
from panelist.views import EmailChangeConfirm, PhoneChangeConfirm

User = get_user_model()


class ProfileTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.manager = ManagerFactory()
        cls.panelist = PanelistFactory(panel__managers=[cls.manager])

    # TODO Should be replaced by a test of qxauth.models.User.get_username()
    def test_username(self):
        email = 'john.doe@qxsms.org'
        phone = '+33666123456'
        p = Profile()
        p.user = User(first_name="John", last_name="Doe", email=email, phone=phone)
        self.assertEqual(p.username, email)
        p.user.email = None
        self.assertEqual(p.username, phone)

    def test_delete_profile_instance_signal(self):
        profile = Profile.objects.first()
        u = profile.user
        profile.delete()
        self.assertEqual(User.objects.filter(email=u.email).count(), 0)

    def test_delete_profile_qs_signal(self):

        u = Profile.objects.first().user
        Profile.objects.all().delete()
        self.assertEqual(User.objects.filter(email=u.email).count(), 0)

    def test_embedded_data_profile(self):
        embedded_data = {
            "id": self.panelist.panelist_id,
            "ess_id": self.panelist.ess_id,
            "sex": self.panelist.sex,
            "country": self.panelist.country,
            "panel": self.panelist.panel.name,
        }
        self.assertEqual(self.panelist.get_embedded_data(), embedded_data)


class EmailChangeIntegrationTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.manager = ManagerFactory()
        cls.panelist = PanelistFactory(panel__managers=[cls.manager])
        cls.panelist.user.set_password('pm')
        cls.panelist.user.save()

    def test_profile_email_change(self):
        self.client.login(email=self.panelist.email, password='pm')

        # Mailbox starts empty
        self.assertFalse(mail.outbox)

        r = self.client.get(reverse('panelist:email-change'))
        self.assertEqual(r.status_code, 200)

        new_email = 'test@qxsms.org'
        # 1) Request email change
        data = {'new_email1': new_email, 'new_email2': new_email}
        r = self.client.post(reverse('panelist:email-change'), data=data)
        self.assertRedirects(r, reverse('panelist:home'))
        profile = Profile.objects.get(email=self.panelist.email)
        self.assertEqual(profile.temp_email, new_email)
        self.assertIsNotNone(profile.temp_email_expiry)

        # 2) An email was sent at the address to be validated
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertListEqual(m.to, [new_email])

        uidb64 = r'(?P<uid>\w+)'
        token = r'(?P<tok>[\w-]+)'
        pattern = parse.unquote(reverse('email-change-confirm', kwargs=dict(uidb64=uidb64, token=token)))
        match = re.search(pattern, m.body, re.MULTILINE)
        self.assertTrue(match)
        (uid, tok) = match.group('uid', 'tok')

        # 3) Complete email change by visiting validation link
        user = User.objects.select_related('profile__panel').get(email=self.panelist.email)
        self.client.get(reverse('email-change-confirm', kwargs={'token': tok, 'uidb64': uid}))
        user.refresh_from_db()
        self.assertEqual(user.email, new_email)
        self.assertEqual(user.profile.email, new_email)
        self.assertIsNone(user.profile.temp_email)
        self.assertIsNone(user.profile.temp_email_expiry)

    def test_profile_email_change_confirm_wronguidb(self):
        tok = "random"
        uid = urlsafe_base64_encode(b'42')
        self.client.get(reverse('email-change-confirm', kwargs={'token': tok, 'uidb64': uid}))


class EmailChangeConfirmTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.panelist = panelist = PanelistFactory()
        cls.user = user = panelist.user
        uid = str(user.pk).encode('utf8')
        cls.uidb64 = urlsafe_base64_encode(uid)

    def setUp(self):
        self.view = EmailChangeConfirm()

    def test_get(self):
        pass

    def test_save_new_email(self):
        self.user.profile.temp_email = 'b@b.org'
        self.user.profile.temp_email_expiry = timezone.now()
        self.view.save_new_email(self.user)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'b@b.org')
        self.assertIsNone(self.user.profile.temp_email)
        self.assertIsNone(self.user.profile.temp_email_expiry)

    def test_get_user(self):
        user = self.view.get_user(self.uidb64)
        self.assertEqual(user.pk, self.user.pk)

    def test_get_user_invalid_uidb64(self):
        uidb64 = urlsafe_base64_encode(b'42')
        self.assertIsNone(self.view.get_user(uidb64))
        uidb64 = 'lkdf\0\0\n\t'
        self.assertIsNone(self.view.get_user(uidb64))

    def test_account_state(self):
        self.assertFalse(self.user.last_login)
        self.assertFalse(self.user.profile.is_opt_out)
        self.assertEqual(self.user.profile.account_state, Profile.ACCOUNT_NOTACTIVATED)

        self.client.force_login(self.user)
        self.assertTrue(self.user.last_login)
        self.assertEqual(self.user.profile.account_state, Profile.ACCOUNT_ACTIVATED)

        self.user.profile.is_opt_out = True
        self.user.profile.save()
        self.assertTrue(self.user.profile.is_opt_out)
        self.assertEqual(self.user.profile.account_state, Profile.ACCOUNT_OPTEDOUT)

        self.user.profile.anonymized_since = timezone.now()
        self.user.profile.save()
        self.assertFalse(self.user.profile.is_active)
        self.assertEqual(self.user.profile.account_state, Profile.ACCOUNT_DEACTIVATED)


class PhoneChangeConfirmTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.panelist = panelist = PanelistFactory()
        cls.user = user = panelist.user
        uid = str(user.pk).encode('utf8')
        cls.uidb64 = urlsafe_base64_encode(uid)

    def setUp(self):
        self.view = PhoneChangeConfirm()

    def test_get_user(self):
        user = self.view.get_user(self.uidb64)
        self.assertEqual(user.pk, self.user.pk)
        self.assertIsNone(self.view.get_user(urlsafe_base64_encode(b'42')))

    def test_save_new_phone(self):
        self.user.profile.temp_phone = '+33612345677'
        self.user.profile.temp_email_expiry = timezone.now()

        self.view.save_new_phone(self.user)

        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, '+33612345677')
        self.assertIsNone(self.user.profile.temp_phone)
        self.assertIsNone(self.user.profile.temp_phone_expiry)


class PhoneChangeIntegrationTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.manager = ManagerFactory()
        cls.panelist = PanelistFactory(panel__managers=[cls.manager])
        cls.panelist.user.set_password('pm')
        cls.panelist.user.save()

    @patch("qxauth.forms.send_single_sms_distribution")
    def test_profile_phone_change(self, send_single_sms_distribution):
        self.client.login(email=self.panelist.email, password='pm')

        r = self.client.get(reverse('panelist:phone-change'))
        self.assertEqual(r.status_code, 200)

        new_prefix = "+33"
        new_number = "198765433"
        new_phone = new_prefix + new_number

        data = {
            'new_phone_number_0': new_prefix, 'confirm_phone_number_0': new_prefix,
            'new_phone_number_1': new_number, 'confirm_phone_number_1': new_number,
        }
        r = self.client.post(reverse('panelist:phone-change'), data=data)
        self.assertRedirects(r, reverse('panelist:home'))
        profile = Profile.objects.get(email=self.panelist.email)
        self.assertEqual(profile.temp_phone, new_phone)
        self.assertIsNotNone(profile.temp_phone_expiry)
        send_single_sms_distribution.assert_called()
        kwargs = send_single_sms_distribution.call_args[1]
        sms_phone = kwargs.get('contact')['phone']
        message = kwargs.get('message')
        self.assertEqual(sms_phone, new_phone[1:])  # Profile.to_json() removes the + sign

        uidb64 = r'(?P<uid>\w+)'
        token = r'(?P<tok>[\w-]+)'
        pattern = parse.unquote(reverse('phone-change-confirm', kwargs=dict(uidb64=uidb64, token=token)))
        match = re.search(pattern, message, re.MULTILINE)
        self.assertTrue(match)
        uid, tok = match.group('uid', 'tok')

        user = User.objects.select_related('profile__panel').get(email=self.panelist.email)
        self.client.get(reverse('phone-change-confirm', kwargs={'token': tok, 'uidb64': uid}))
        user.refresh_from_db()
        self.assertEqual(user.phone, new_phone)
        self.assertEqual(user.profile.phone, new_phone)
        self.assertIsNone(user.profile.temp_phone)
        self.assertIsNone(user.profile.temp_phone_expiry)

    @patch("qxauth.forms.send_single_sms_distribution")
    def test_profile_phone_change_diff_phone(self, send_single_sms_distribution):
        self.client.login(email=self.panelist.email, password='pm')

        r = self.client.get(reverse('panelist:phone-change'))
        self.assertEqual(r.status_code, 200)

        new_prefix = "+33"
        new_number = "198765433"

        data = {
            'new_phone_number_0': new_prefix, 'confirm_phone_number_0': new_prefix,
            'new_phone_number_1': new_number, 'confirm_phone_number_1': "198765434",
        }
        r = self.client.post(reverse('panelist:phone-change'), data=data)
        self.assertEqual(r.status_code, 200)
        send_single_sms_distribution.assert_not_called()

    @patch("qxauth.forms.send_single_sms_distribution")
    def test_profile_phone_change_existing_phone(self, send_single_sms_distribution):
        self.client.login(email=self.panelist.email, password='pm')

        r = self.client.get(reverse('panelist:phone-change'))
        self.assertEqual(r.status_code, 200)
        actual_phone = str(self.panelist.phone)

        new_prefix = actual_phone[0:3]
        new_number = actual_phone[3:]

        data = {'new_phone_number_0': new_prefix, 'confirm_phone_number_0': new_prefix,
                'new_phone_number_1': new_number, 'confirm_phone_number_1': "198765432"}
        r = self.client.post(reverse('panelist:phone-change'), data=data)
        self.assertEqual(r.status_code, 200)
        send_single_sms_distribution.assert_not_called()

    def test_profile_phone_change_confirm_wronguidb(self):
        tok = "random"
        uid = urlsafe_base64_encode(b'42')
        self.client.get(reverse('phone-change-confirm', kwargs={'token': tok, 'uidb64': uid}))


class ProfileDeactivationTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.manager = ManagerFactory()

    def setUp(self) -> None:
        self.panelist = PanelistFactory(panel__managers=[self.manager])

    # Proper values are set when profile is deactivated
    def test_deactivation_values(self):
        self.assertTrue(self.panelist.user.is_active)
        self.assertFalse(self.panelist.is_opt_out)
        self.assertFalse(self.panelist.opt_out_date)
        self.assertFalse(self.panelist.delete_contact_data)
        self.assertFalse(self.panelist.anonymized_since)

        self.panelist.deactivate()

        self.assertFalse(self.panelist.user.is_active)
        self.assertTrue(self.panelist.is_opt_out)
        self.assertTrue(self.panelist.opt_out_date)  # Filled when profile was not opt out before
        self.assertTrue(self.panelist.delete_contact_data)
        self.assertTrue(self.panelist.anonymized_since)

    # The profile is set to readonly when it is deactivated
    def test_deactivated_readonly_profile(self):
        anonymized_values = self.panelist.anonymized_values

        # Change the name to a random one
        self.panelist.first_name = str(self.panelist.uid)
        self.panelist.save()

        # Deactivate the panelist, this should remove their name
        self.panelist.deactivate()
        # Check that the name has been anonymized
        self.assertEqual(self.panelist.first_name, anonymized_values["first_name"])

        # Set a new name: this should not work since a deactivated profile is readonly
        self.client.login(username=self.manager.email, password="nc")
        self.client.post(
            reverse("manager:panel-member-update", args=[self.panelist.pk]),
            {"first_name": "CANNOTCHANGEME"}
        )

        # The first name should not change
        self.panelist = Profile.objects.get(pk=self.panelist.pk)
        self.assertEqual(self.panelist.first_name, anonymized_values["first_name"])

    def test_deactivation_rights(self):
        self.assertTrue(self.panelist.is_active)

        self.client.login(username=self.manager.email, password="nc")
        r = self.client.post(reverse("manager:panel-member-deactivate", args=[self.panelist.pk]), follow=True)
        self.assertRedirects(r, reverse("manager:panel-member-update", args=[self.panelist.pk]))
        self.assertContains(r, "Deactivated panelist")

        self.panelist = Profile.objects.get(pk=self.panelist.pk)
        self.assertFalse(self.panelist.is_active)

    # Only users managing the panel can deactivate the profile
    def test_deactivation_no_rights(self):
        self.assertTrue(self.panelist.is_active)

        new_manager = ManagerFactory()
        self.client.login(username=new_manager.email, password="nc")
        r = self.client.post(reverse("manager:panel-member-deactivate", args=[self.panelist.pk]))
        self.assertTrue(isinstance(r, HttpResponseNotFound))

        self.panelist = Profile.objects.get(pk=self.panelist.pk)
        self.assertTrue(self.panelist.is_active)

    def test_anonymization(self):
        anonymized_values = self.panelist.anonymized_values

        self.panelist.first_name = str(self.panelist.uid)
        self.panelist.save()

        self.panelist.deactivate()

        # Checking anonymized fields
        for key, value in anonymized_values.items():
            self.assertEqual(getattr(self.panelist, key), value)

    def test_anonymized_values_present_view(self):
        self.client.login(username=self.manager.email, password="nc")
        r = self.client.get(reverse("manager:panel-member-deactivate", args=[self.panelist.pk]))
        self.assertEqual(r.context["anonymized_values"], self.panelist.anonymized_values)
