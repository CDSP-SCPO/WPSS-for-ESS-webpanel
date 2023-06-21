# -- STDLIB
from unittest.mock import patch

# -- DJANGO
from django.contrib.auth.models import Group
from django.test import TestCase

# -- QXSMS
from hq.forms import ManagerCreateForm


class ManagerCreateFormTestCase(TestCase):

    @patch('django.contrib.auth.base_user.AbstractBaseUser.set_password')
    @patch('django.contrib.auth.base_user.BaseUserManager.make_random_password')
    def test_make_random_password_is_called(self, make_random_password, set_password):
        Group.objects.create(name='Managers')
        make_random_password.return_value = 'password'
        data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'email': 'test@gmail.com'
        }
        form = ManagerCreateForm(data)
        self.assertTrue(form.is_valid())
        form.save()
        set_password.assert_called_once_with('password')
