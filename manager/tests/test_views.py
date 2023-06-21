# -- STDLIB
import csv
import io
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# -- DJANGO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import resolve_url, reverse
from django.test import TestCase, TransactionTestCase, modify_settings
from django.test.utils import override_settings

# -- QXSMS
from distributions.client import parse_datetime
from distributions.factories import (
    LinkDistributionFactory, MessageDistributionFactory,
)
from distributions.models import Link, MessageDistribution
from hq.factories import HqFactory, PanelFactory
from manager.factories import GroupTaskImportFactory, ManagerFactory
from manager.forms import CSVImportForm
from manager.models import GroupTaskImport
from panelist.factories import PanelistFactory
from panelist.models import BlankSlot, BlankSlotValue, Profile
from qxauth.models import User
from qxsms import settings
from utils.csvimport import FIELD_MAP


class MemberTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.manager = ManagerFactory()
        cls.profile = PanelistFactory(panel__managers=[cls.manager])

    def setUp(self):
        self.client.force_login(self.manager)

    def test_profile_update(self):
        url = resolve_url('manager:panel-member-update', pk=self.profile.pk)
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'manager/panel_member_update.html')
        response = self.client.post(url, {
            'ess_id': self.profile.ess_id,
            'first_name': 'John',
            'last_name': 'Doe',
            'country': self.profile.country,
            'day_of_birth': self.profile.day_of_birth,
            'education_years': self.profile.education_years,
            'email': self.profile.email,
            'internet_use': self.profile.internet_use,
            'month_of_birth': self.profile.month_of_birth,
            'phone': self.profile.phone,
            'sex': self.profile.sex,
            'year_of_birth': self.profile.year_of_birth,
            'language': 'FR',
        }, follow=True)

        self.assertRedirects(response, resolve_url('manager:panel-member-list', pk=self.profile.panel.pk))
        self.assertContains(response, "Updated panelist John Doe")

    def test_profile_delete(self):
        url = reverse('manager:panel-member-delete', args=[self.profile.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'manager/panel_member_confirm_delete.html')

        response = self.client.post(url)
        redirect_url = reverse('manager:panel-member-list', args=[self.profile.panel.pk])
        self.assertRedirects(response, redirect_url)
        self.assertQuerysetEqual(Profile.objects.all(), [])
        self.assertQuerysetEqual(User.objects.filter(groups__name=settings.QXSMS_GROUP_PANEL_MEMBERS), [])

    def test_profile_create(self):
        url = reverse('manager:panel-member-create', args=[self.profile.panel.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].initial['panel'], self.profile.panel.pk)
        self.client.post(url, {
            'ess_id': self.profile.ess_id + 1,
            'sex': 1,
            'email': 'foo@bar.com',
            'country': 'FR',
            'internet_use': 1,
            'education_years': 2,
            'day_of_birth': 1,
            'month_of_birth': 1,
            'year_of_birth': 1900,
            'language': 'FR',
        })
        self.assertTrue(Profile.objects.filter(email="foo@bar.com").exists())
        self.assertTrue(User.objects.filter(email="foo@bar.com").exists())

    def test_profile_create_unique_together_error(self):
        """Form displays a validation error if (ess_id, panel) is not unique"""

        existing_ess_id = Profile.objects.all()[0].ess_id
        self.assertTrue(Profile.objects.filter(ess_id=existing_ess_id, panel=self.profile.panel).exists())
        url = reverse('manager:panel-member-create', args=[self.profile.panel.pk])
        response = self.client.post(url, {
            'ess_id': existing_ess_id,
            'sex': 1,
            'email': 'foo@bar.com',
            'country': 'FR',
            'internet_use': 1,
            'education_years': 2,
            'day_of_birth': 1,
            'month_of_birth': 1,
            'year_of_birth': 1900
        })
        self.assertFormError(response, 'form', None, "Profile with this Panel and Ess id already exists.")


class BlankSlotValueTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hq = HqFactory()
        cls.nc = ManagerFactory()
        cls.pm = PanelistFactory(panel__managers=[cls.nc])
        cls.blank_slot = BlankSlot.objects.create(name='blank_slot_name', description='blank_slot_description')

    def test_blank_slot_value_list_forbidden(self):
        second_manager = ManagerFactory()
        self.client.force_login(second_manager)
        url = reverse('manager:blankslotvalue-list', args=[self.pm.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class CSVExportTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.nc = ManagerFactory()
        cls.pm = PanelistFactory(panel__managers=[cls.nc])

    def setUp(self) -> None:
        self.client.force_login(self.nc)
        self.url = resolve_url('manager:panel-member-export', pk=self.pm.panel.pk)

    def test_export_CSV(self):
        expect_headers = [
            'idno',
            'name',
            'surname',
            'sex',
            'email',
            'mobile',
            'propertyname',
            'number',
            'address',
            'address2',
            'city',
            'county',
            'postcode',
            'cntry',
            'lng',
            'netusoft',
            'eduyrs',
            'dybrn',
            'mthbrn',
            'yrbrn',
            'opto',
            'dopto',
            'ropto',
            'delcontactdata',
            'delsurveydata',
            'movcntry',
            'noincen',
            'nolett',
            'notxt',
            'noem',
        ]
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        reader = csv.DictReader(io.StringIO(content))
        self.assertSetEqual(set(reader.fieldnames), set(expect_headers))

    def test_export_csv_all_fields(self):
        response = self.client.get(self.url, {'all': ''})
        content = response.content.decode()
        reader = csv.DictReader(io.StringIO(content))
        self.assertSetEqual(set(reader.fieldnames), set(FIELD_MAP.values()))

    def test_export_CSV_customize(self):
        url = resolve_url('manager:panel-member-export-custom', pk=self.pm.panel.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context.get('panel'))
        response = self.client.post(url, {'panelist_id': True, 'age': True})
        f = io.StringIO(response.content.decode())
        reader = csv.DictReader(f)
        self.assertListEqual(reader.fieldnames, ['age', 'uid'])


class CSVImportTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.nc = ManagerFactory()
        cls.panel = PanelFactory(managers=[cls.nc])

    def setUp(self):
        self.client.force_login(self.nc)
        self.url = reverse('manager:panel-member-import', args=[self.panel.pk])

    def test_csv_import_form(self):
        with self.settings(DEBUG=True):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], CSVImportForm)
        # this does not work because the CSVImportForm used by self.client is not imported with correct DEBUG value:
        # self.assertIsInstance(response.context["form"].fields['dry_run'].widget, forms.CheckboxInput)
        with self.settings(DEBUG=False):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], CSVImportForm)
        # this does not work because the CSVImportForm used by self.client is not imported with correct DEBUG value:
        # self.assertIsInstance(response.context["form"].fields['dry_run'].widget, forms.HiddenInput)

    @override_settings(DEBUG=True)
    @patch('manager.views.get_task_info')
    @patch('manager.views.import_data_celery')
    def test_csv_import(self, import_data_celery, get_task_info):
        gt = GroupTaskImport.objects.create(file_name="file.csv",
                                            dry_run=False, panel_id=self.panel.pk)
        import_data_celery.return_value = gt
        results = {"new": 10, "update": 0, "delete": 0, "skip": 0, "error": 0, "invalid": 0}
        get_task_info.return_value = {"results": results, "errors": {}, "completed": True, "dry_run": False}

        profile = {
            'idno': '1',
            'sex': '1',
            'email': 'foo@gmail.com',
            'cntry': 'FR',
            'netusoft': '1',
            'eduyrs': '2',
            'dybrn': '1',
            'mthbrn': '1',
            'yrbrn': '1900'
        }
        f = io.StringIO()
        writer = csv.DictWriter(f, fieldnames=list(profile))
        writer.writeheader()
        writer.writerow(profile)
        f.seek(0)
        response = self.client.post(self.url, {'dataset': f}, follow=True)
        self.assertEqual(import_data_celery.call_count, 1)
        self.assertEqual(response.status_code, 200)
        get_task_info.assert_called_with(self.panel.pk, gt.id)


class PanelUpdateTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.nc = ManagerFactory()
        cls.panel = PanelFactory(managers=[cls.nc])

    def test_panel_update_redirect(self):
        self.client.force_login(self.nc)
        url = resolve_url('manager:panel-update', pk=self.panel.pk)
        response = self.client.post(url, {
            'incentive_amount': "5€",
            'contact_info': "HELP YOURSELF",
        }, follow=True)
        self.assertRedirects(response, resolve_url('manager:panel-detail', pk=self.panel.pk))
        self.assertContains(response, "Updated panel level variables")


class BlankSLotExportCSVTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.nc = ManagerFactory()
        cls.pm = PanelistFactory(panel__managers=[cls.nc])
        BlankSlot.objects.create(name='blankslot', description="description")
        cls.panel = cls.pm.panel

    def test_export_sample(self):
        self.client.force_login(self.nc)
        url = resolve_url('manager:members-import-sample')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_export_CSV(self):
        self.client.force_login(self.nc)
        url = resolve_url('manager:panel-blank-slot-export', panel_pk=self.panel.pk)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

    def test_export_CSV_bad_panel(self):
        self.client.force_login(self.nc)
        url = resolve_url('manager:panel-blank-slot-export', panel_pk=self.panel.pk+1)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)


class BlankSLotImportCSVTestCase(TestCase):

    def setUp(self):
        self.nc = ManagerFactory()
        self.pm = PanelistFactory(panel__managers=[self.nc])
        bk = BlankSlot.objects.create(name='blankslot', description="description")
        BlankSlotValue.objects.create(blankslot=bk, profile=self.pm, value='value')
        self.client.force_login(self.nc)
        self.panel = self.pm.panel

    def test_import_CSV(self):
        content = "idno,cntry,addvar,value\n{},{},blankslot,new_value".format(self.pm.ess_id, self.pm.country)
        file = SimpleUploadedFile.from_dict(dict(
            filename="file.csv",
            content=bytes(content, 'utf8'),
            content_type='text/csv'
        ))

        url = resolve_url('manager:panel-blank-slot-import', pk=self.panel.pk)
        response = self.client.post(url, {'dataset': file}, format='multipart', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 additional variables updated')
        self.assertEqual(BlankSlotValue.objects.all()[0].value, "new_value")

    def test_wrong_import_CSV(self):
        # Import with no changes
        content = "idno,cntry,addvar,value\n{},{},blankslot,value".format(self.pm.ess_id, self.pm.country)
        file = SimpleUploadedFile.from_dict(dict(
            filename="file.csv",
            content=bytes(content, 'utf8'),
            content_type='text/csv'
        )
        )

        url = resolve_url('manager:panel-blank-slot-import', pk=self.panel.pk)
        response = self.client.post(url, {'dataset': file}, format='multipart', follow=True)
        self.assertContains(response, '0 additional variables updated')

    def test_create_blank_slot_value_import_CSV(self):
        nb_bkv = BlankSlotValue.objects.all().count()
        BlankSlot.objects.create(name='blankslot1', description="description1")
        content = "idno,cntry,addvar,value\n{},{},blankslot1,new_value".format(self.pm.ess_id, self.pm.country)
        file = SimpleUploadedFile.from_dict(dict(
            filename="file.csv",
            content=bytes(content, 'utf8'),
            content_type='text/csv'
        )
        )
        url = resolve_url('manager:panel-blank-slot-import', pk=self.panel.pk)
        response = self.client.post(url, {'dataset': file}, format='multipart', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 additional variables created')
        self.assertEqual(BlankSlotValue.objects.all().count(), nb_bkv + 1)

    def test_wrong_panel(self):
        panel2 = PanelFactory(managers=[self.nc])
        pm2 = PanelistFactory(panel=panel2)
        content = "idno,cntry,addvar,value\n{},{},blankslot,new_value".format(pm2.ess_id, pm2.country)
        file = SimpleUploadedFile.from_dict(dict(
            filename="file.csv",
            content=bytes(content, 'utf8'),
            content_type='text/csv'
        )
        )
        url = resolve_url('manager:panel-blank-slot-import', pk=self.panel.pk)
        response = self.client.post(url, {'dataset': file}, format='multipart', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Attempted modifications outside of current panel.')


@modify_settings(MIDDLEWARE={'remove': 'qxsms.middleware.AuthorizationMiddleware'})
class BlankSlotValueUpdateTestCase(TransactionTestCase):

    def setUp(self):
        self.nc = ManagerFactory()
        self.panelist = PanelistFactory(panel__managers=[self.nc])
        self.url = reverse('manager:blankslotvalue-update', args=[self.panelist.pk])
        self.client.force_login(self.nc)

    def test_redirect(self):
        response = self.client.post(self.url, data={
            'form-TOTAL_FORMS': 0,
            'form-INITIAL_FORMS': 0,
            'form-MAX_NUM_FORMS': 1000
        })
        success_url = reverse('manager:blankslotvalue-list', args=[self.panelist.pk])
        self.assertRedirects(response, success_url)

    def test_forbidden(self):
        self.nc.panel_set.set([])
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)


class PanelSurveyDetailTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.manager = ManagerFactory()
        cls.first_panel = PanelFactory(managers=[cls.manager])
        PanelistFactory.create_batch(3, panel=cls.first_panel)
        cls.link_distribution = LinkDistributionFactory(panels=[cls.first_panel], create_links=True)

        for i, x in enumerate(Link.objects.all()):
            x.qx_contact_id = 'CID_{}'.format((i))
            x.url = 'URL_{}'.format((i))
            x.save()

        cls.history = [
            {
                'contactId': 'CID_0',
                'status': 'Pending',
                'openedAt': '2021-05-01T10:10:13.000Z',
                'responseStartedAt': '2021-05-01T10:10:13.000Z',
                'responseCompletedAt': '2021-05-01T10:10:24.000Z',
            },
            {
                'contactId': 'CID_1',
                'status': 'SurveyFinished',
                'openedAt': '2021-06-01T10:10:13.000Z',
                'responseStartedAt': '2021-06-01T10:10:13.000Z',
                'responseCompletedAt': '2021-06-01T10:10:24.000Z',
            },
            {
                'contactId': 'CID_2',
                'status': 'SurveyStarted',
                'openedAt': '2021-07-01T10:10:13.000Z',
                'responseStartedAt': '2021-07-01T10:10:13.000Z',
                'responseCompletedAt': '2021-07-01T10:10:24.000Z',
            },

        ]

    def setUp(self):
        self.client.force_login(self.manager)
        self.url = resolve_url('manager:panel-survey-detail',
                               pk=self.first_panel.pk,
                               linkdistribution_pk=self.link_distribution.pk
                               )

    @patch('distributions.services.get_distribution_history')
    def test_sort_by_full_name(self, get_distribution_history):
        get_distribution_history.return_value = self.history
        full_name = [f"{x.last_name} {x.first_name}" for x in Profile.objects.filter(panel=self.first_panel.pk)]

        response = self.client.get(self.url, {'order_by': 'full_name', 'sort': 'desc', })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'][0]['full_name'], sorted(full_name, reverse=True)[0])

        response = self.client.get(self.url, {'order_by': 'full_name', 'sort': 'asc', })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'][0]['full_name'], sorted(full_name)[0])

    @patch('distributions.services.get_distribution_history')
    def test_sort_by_date(self, get_distribution_history):
        get_distribution_history.return_value = self.history
        started_dates = [h['responseStartedAt'] for h in self.history[:3]]

        response = self.client.get(self.url, {'order_by': 'started_at', 'sort': 'asc', })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'][0]['started_at'], parse_datetime(sorted(started_dates)[0]))

        response = self.client.get(self.url, {'order_by': 'started_at', 'sort': 'desc', })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'][0]['started_at'],
                         parse_datetime(sorted(started_dates, reverse=True)[0]))

    @patch('distributions.services.get_distribution_history')
    def test_key_error_sort(self, get_distribution_history):
        get_distribution_history.return_value = self.history
        response = self.client.get(self.url, {'order_by': 'error', 'sort': 'asc', })
        self.assertEqual(response.status_code, 404)

    @patch('distributions.services.get_distribution_history')
    def test_stats_by_panel(self, get_distribution_history):
        get_distribution_history.return_value = self.history
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        stats = response.context['records_stats'][self.first_panel.name]
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['not_started'], 1)
        self.assertEqual(stats['started'], 1)

    @patch('distributions.services.get_distribution_history')
    def test_ling_without_url(self, get_distribution_history):
        '''
        Test that a link without url (happens when a panelist is opt-out) is not counted in the total of stats
        '''
        link = Link.objects.all()[0]
        link.url = ''
        link.save()
        get_distribution_history.return_value = self.history
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        stats = response.context['records_stats'][self.first_panel.name]
        self.assertEqual(stats['total'], 2)


class MessageDistributionListTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.m_1 = ManagerFactory()
        cls.pm_1 = PanelistFactory(panel__managers=[cls.m_1])
        cls.link_distribution_1 = LinkDistributionFactory(panels=[cls.pm_1.panel], create_links=True)
        cls.message_distribution_1 = MessageDistributionFactory(link_distribution=cls.link_distribution_1,
                                                                links=cls.link_distribution_1.links.all())

        cls.m_2 = ManagerFactory()
        cls.pm_2 = PanelistFactory(panel__managers=[cls.m_2])
        cls.link_distribution_2 = LinkDistributionFactory(panels=[cls.pm_2.panel], create_links=True)
        cls.message_distribution_2 = MessageDistributionFactory(link_distribution=cls.link_distribution_2,
                                                                links=cls.link_distribution_2.links.all())

    def test_wrong_panel_manager(self):
        self.client.force_login(self.m_2)
        url = resolve_url('manager:msg-distribution-list', pk=self.pm_1.panel.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_dislpay_only_panel_stats(self):
        self.client.force_login(self.m_1)
        url = resolve_url('manager:msg-distribution-list', pk=self.pm_1.panel.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 1)


class MessageDistributionDetailTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.m_1 = ManagerFactory()
        cls.pm_1 = PanelistFactory(panel__managers=[cls.m_1])
        cls.link_distribution_1 = LinkDistributionFactory(panels=[cls.pm_1.panel], create_links=True)
        cls.message_distribution_email = MessageDistributionFactory(link_distribution=cls.link_distribution_1,
                                                                    links=cls.link_distribution_1.links.all())
        cls.message_distribution_sms = MessageDistributionFactory(link_distribution=cls.link_distribution_1,
                                                                  links=cls.link_distribution_1.links.all(),
                                                                  contact_mode=MessageDistribution.MODE_SMS)
        cls.history = [
            {'contactId': 'CID_1', 'status': 'Success'},
            {'contactId': 'CID_2', 'status': 'Success'},
            {'contactId': 'CID_3', 'status': 'Opened'},
            {'contactId': 'CID_4', 'status': 'Opened'},
            {'contactId': 'CID_5', 'status': 'HardBounce'},
            {'contactId': 'CID_6', 'status': 'SoftBounce'},
            {'contactId': 'CID_7', 'status': 'Other'},
        ]

    def test_wrong_manager(self):
        m_2 = ManagerFactory()
        self.client.force_login(m_2)
        url = resolve_url('manager:msg-distribution-detail', pk=self.pm_1.panel.pk,
                          msgdist_pk=self.message_distribution_email.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @patch('distributions.services.get_distribution_history')
    def test_history(self, get_distribution_history):
        get_distribution_history.return_value = self.history
        self.message_distribution_email.qx_id = 'EMD_1'
        self.message_distribution_email.save()
        self.client.force_login(self.m_1)
        url = resolve_url('manager:msg-distribution-detail', pk=self.pm_1.panel.pk,
                          msgdist_pk=self.message_distribution_email.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        get_distribution_history.assert_called_with(qx_id='EMD_1', skip_cache=False)

    @patch('distributions.services.get_distribution_history')
    def test_display_schedule(self, get_distribution_history):
        get_distribution_history.return_value = self.history
        self.message_distribution_email.qx_id = 'EMD_1'
        self.message_distribution_email.send_date = datetime.now(timezone.utc) + timedelta(days=1)
        self.message_distribution_email.save()
        self.client.force_login(self.m_1)
        url = resolve_url('manager:msg-distribution-detail', pk=self.pm_1.panel.pk,
                          msgdist_pk=self.message_distribution_email.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['schedule'], True)
        self.assertEqual(response.context['days'], 0)

    @patch('distributions.services.get_distribution_history')
    def test_filter(self, get_distribution_history):
        get_distribution_history.return_value = self.history
        PanelistFactory.create_batch(6, panel=self.pm_1.panel)
        link_distribution = LinkDistributionFactory(panels=[self.pm_1.panel], create_links=True)
        message_distribution = MessageDistributionFactory(link_distribution=link_distribution,
                                                          links=link_distribution.links.all(), qx_id='EMD_1')
        for i, l in enumerate(Link.objects.all()):
            l.qx_contact_id = 'CID_{}'.format(i)
            l.save()

        self.client.force_login(self.m_1)
        url = resolve_url('manager:msg-distribution-detail', pk=self.pm_1.panel.pk,
                          msgdist_pk=message_distribution.pk)
        response = self.client.get(url, {'status': 'Opened'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['profiles']), 2)

        response = self.client.get(url, {'status': 'Success'})
        self.assertEqual(len(response.context['profiles']), 4)

        response = self.client.get(url, {'status': 'HardBounce'})
        self.assertEqual(len(response.context['profiles']), 1)

        response = self.client.get(url, {'status': 'Other_Failures'})
        self.assertEqual(len(response.context['profiles']), 1)


class LinkDistributionExportTestCase(TestCase):

    def setUp(self) -> None:
        self.m_1 = ManagerFactory()
        self.pm_1 = PanelistFactory(panel__managers=[self.m_1])
        self.pm_2 = PanelistFactory(panel=self.pm_1.panel)
        self.link_distribution_1 = LinkDistributionFactory(panels=[self.pm_1.panel], create_links=True)
        self.history = [
                          {'contactId': str(self.pm_1.ess_id), 'status': 'Pending', },
                          {'contactId': str(self.pm_2.ess_id), 'status': 'SurveyFinished', },
        ]
        first_link = Link.objects.all().first()
        second_link = Link.objects.all()[1]
        first_link.qx_contact_id = self.pm_1.ess_id
        second_link.qx_contact_id = self.pm_2.ess_id
        first_link.save()
        second_link.save()
        self.client.force_login(self.m_1)
        self.url = resolve_url('manager:panel-survey-links-export',
                               pk=self.pm_1.panel.pk,
                               linkdistribution_pk=self.link_distribution_1.pk)

    @patch('distributions.services.get_distribution_history')
    def test_export(self, get_distribution_history):
        get_distribution_history.return_value = self.history
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            if row['ess_id'] == str(self.pm_1.ess_id):
                self.assertEqual(row['status'], 'Pending')
            if row['ess_id'] == str(self.pm_2.ess_id):
                self.assertEqual(row['status'], 'SurveyFinished')


class PanelSurveyListViewTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.m_1 = ManagerFactory()
        cls.pm_1 = PanelistFactory(panel__managers=[cls.m_1])
        cls.link_distribution_1 = LinkDistributionFactory(panels=[cls.pm_1.panel],
                                                          qx_created_date=datetime.now(timezone.utc))
        cls.link_distribution_2 = LinkDistributionFactory(panels=[cls.pm_1.panel],
                                                          qx_created_date=datetime.now(timezone.utc) + timedelta(
                                                              days=1))
        cls.link_distribution_3 = LinkDistributionFactory(panels=[cls.pm_1.panel],
                                                          qx_created_date=datetime.now(timezone.utc) - timedelta(
                                                              days=1))

    def test_export(self):
        self.client.force_login(self.m_1)
        url = resolve_url('manager:panel-survey-list', pk=self.pm_1.panel.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'][0], self.link_distribution_2)
        self.assertEqual(response.context['object_list'][1], self.link_distribution_1)
        self.assertEqual(response.context['object_list'][2], self.link_distribution_3)


class TaskImportListTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.nc = ManagerFactory()
        cls.panel = PanelFactory(managers=[cls.nc])

    def setUp(self):
        self.client.force_login(self.nc)

    def test_order(self):
        first_import = GroupTaskImportFactory(panel=self.panel)
        second_import = GroupTaskImportFactory(panel=self.panel)
        url = resolve_url('manager:task-import-list', pk=self.panel.pk)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'][0], second_import)

        response = self.client.get(url, {'sort': 'asc'})
        self.assertEqual(response.context['object_list'][0], first_import)
