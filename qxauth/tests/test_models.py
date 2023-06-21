# -- DJANGO
from django.contrib.auth import get_user_model
from django.test import TestCase

# -- THIRDPARTY
from phonenumber_field.phonenumber import PhoneNumber

User = get_user_model()


class QxsmsUserManagerTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email='user@qxsms.eu', password='u', phone='+33666618542')

    def test_get_user_by_email(self):
        user = User.objects.get_by_natural_key('user@qxsms.eu')
        self.assertEqual(user.id, self.user.id)

    def test_get_user_by_phone(self):
        phone = PhoneNumber.from_string("+33666618542")
        user = User.objects.get_by_natural_key(phone)
        self.assertEqual(user.id, self.user.id)

    def test_phone_cannot_be_string(self):
        with self.assertRaises(User.DoesNotExist):
            User.objects.get_by_natural_key('+33666618542')


class UserTestCase(TestCase):

    def test_blank_email_saved_as_null(self):
        u = User(email="", phone="+33666666666")
        u.save()
        u.refresh_from_db()
        self.assertIsNone(u.email)

    def test_blank_phone_saved_as_null(self):
        u = User(email="foo@bar.com", phone="")
        u.save()
        u.refresh_from_db()
        self.assertIsNone(u.phone)
