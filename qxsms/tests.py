# -- DJANGO
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import reverse
from django.test import TestCase
from django.test.utils import modify_settings
from django.utils import translation

# -- QXSMS
from hq.factories import HqFactory
from manager.factories import ManagerFactory

User = get_user_model()


class ManagerProfileUpdateTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.hq = HqFactory()
        cls.manager = ManagerFactory()

    def test_hq_update_nc(self):
        self.client.login(email=self.hq.email, password='hq')
        nc = User.objects.get(email=self.manager.email)
        nc_modified = {'first_name': 'monde', 'last_name': 'coordinator', 'email': 'nc@mail.com'}
        self.client.post(reverse('hq:manager-update', kwargs={'pk': nc.pk}), nc_modified)
        nc.refresh_from_db()
        self.assertEqual(nc.first_name, 'monde')

    def test_nc_update_self(self):
        self.client.login(email=self.manager.email, password='nc')
        nc_modified = {'first_name': 'national', 'last_name': 'manager', 'email': 'nc@mail.com'}
        r = self.client.post(reverse('manager:profile-update'), nc_modified, follow=True)
        self.assertEqual(r.context['user'].last_name, 'manager')

    def test_hq_desactive_nc(self):
        self.client.login(email=self.hq.email, password='hq')
        nc = User.objects.get(email=self.manager.email)
        nc_modified = {'first_name': 'national', 'last_name': 'coordinator', 'email': 'nc@mail.com',
                       'is_active': False}
        self.client.post(reverse('hq:manager-update', kwargs={'pk': nc.pk}), nc_modified)
        nc.refresh_from_db()
        self.assertFalse(nc.is_active)

    def test_hq_delete_nc(self):
        self.client.login(email=self.hq.email, password='hq')
        nc = User.objects.get(email=self.manager.email)
        r = self.client.post(reverse('hq:manager-delete', kwargs={'pk': nc.pk}), follow=True)
        self.assertFalse(nc in r.context['object_list'])


@modify_settings(
    MIDDLEWARE={
        'remove': ['qxsms.middleware.AuthorizationMiddleware']
    }
)
class ForceEnglishMiddlewareTestCase(TestCase):

    def test_panelist_french(self):
        r = self.client.get(reverse('panelist:email-change'), HTTP_ACCEPT_LANGUAGE='fr')
        self.assertEqual(r['Content-Language'], 'fr')

    def test_hq_english_enforced(self):
        r = self.client.get(reverse('hq:home'), HTTP_ACCEPT_LANGUAGE='fr')
        self.assertEqual(r['Content-Language'], settings.LANGUAGE_CODE)
        self.assertEqual(self.client.session[translation.LANGUAGE_SESSION_KEY], settings.LANGUAGE_CODE)

    def test_nc_english_enforced(self):
        r = self.client.get(reverse('manager:home'), HTTP_ACCEPT_LANGUAGE='fr')
        self.assertEqual(r['Content-Language'], settings.LANGUAGE_CODE)
        self.assertEqual(self.client.session[translation.LANGUAGE_SESSION_KEY], settings.LANGUAGE_CODE)
