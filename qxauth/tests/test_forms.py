# -- DJANGO
from django.test import TestCase

# -- QXSMS
from manager.factories import ManagerFactory
from panelist.factories import PanelistFactory
from qxauth.forms import QxsmsAuthByEmailForm, QxsmsAuthByPhoneForm


class LoginFormTestCase(TestCase):
    def setUp(self):
        m = ManagerFactory()
        pm = PanelistFactory(panel__managers=[m])

        actual_phone = str(pm.phone)
        prefix = actual_phone[0:3]
        number = actual_phone[3:]

        self.data = {
            'username': pm.email,
            'username_0': prefix,
            'username_1': number,
            'password': "pm",
        }

    def test_email_login_form(self):
        form = QxsmsAuthByEmailForm(None, self.data)
        self.assertTrue(form.is_valid())

    def test_phone_login_form(self):
        form = QxsmsAuthByPhoneForm(None, self.data)
        self.assertTrue(form.is_valid())
