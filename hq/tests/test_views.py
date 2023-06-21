# -- STDLIB
from unittest.mock import patch

# -- DJANGO
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import resolve_url
from django.test import TestCase, TransactionTestCase, modify_settings
from django.urls import reverse

# -- QXSMS
from distributions.factories import (
    LinkDistributionFactory, MessageDistributionFactory,
)
from distributions.models import MessageDistribution
from hq.factories import HqFactory
from hq.models import Panel
from manager.factories import ManagerFactory
from panelist.factories import PanelistFactory
from panelist.models import BlankSlot, BlankSlotValue, Profile

User = get_user_model()


class PanelTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.hq = HqFactory()
        cls.manager = ManagerFactory()
        cls.panelist = PanelistFactory(panel__managers=[cls.manager])

    def setUp(self):
        self.client.login(username=self.hq.email, password='hq')

    def test_panel_create(self):
        # One panel to begin with
        self.assertEqual(Panel.objects.count(), 1)

        # Create a panel
        name = 'test panel'
        url = reverse('hq:panel-create')
        response = self.client.post(url, {
            'name': name,
            'managers': [self.manager.pk]
        }, follow=True)

        # Panel with given name and manager are found in the database
        self.assertEqual(Panel.objects.count(), 2)
        p = Panel.objects.get(name=name)
        self.assertSetEqual(set(p.managers.all()), {self.manager})

        # Check redirection
        self.assertRedirects(response, reverse('hq:panel-list'))
        self.assertContains(response, "Created panel")
        self.assertContains(response, f"managed by {self.manager}")

    def test_panel_update(self):
        # One panel to begin with
        self.assertEqual(Panel.objects.count(), 1)
        p = Panel.objects.first()
        name = 'new name'

        url = reverse('hq:panel-update', args=(p.pk,))
        response = self.client.post(url, {
            'name': name,
        }, follow=True)

        # Panel updated successfully
        p.refresh_from_db()
        self.assertEqual(p.name, name)

        # Check redirection
        self.assertRedirects(response, reverse('hq:panel-detail', args=(p.pk,)))
        self.assertContains(response, 'Updated Panel')

    def test_panel_manager_assign(self):
        m = ManagerFactory()
        url = reverse('hq:panel-assign', args=(self.panelist.panel.pk,))
        response = self.client.post(url, {
            'managers': [m.pk]
        }, follow=True)
        self.assertSetEqual(set(self.panelist.panel.managers.all()), {self.manager, m})
        self.assertRedirects(response, reverse('hq:panel-detail', args=(self.panelist.panel.pk,)))
        self.assertContains(response, f"Assigned manager(s) {m.email}")

    def test_panel_manager_unassign(self):
        url = reverse('hq:panel-unassign', args=(self.panelist.panel.pk,))
        response = self.client.post(url, {
            'manager': self.manager.pk
        }, follow=True)
        self.assertEqual(self.panelist.panel.managers.count(), 0)
        self.assertRedirects(response, reverse('hq:panel-detail', args=(self.panelist.panel.pk,)))
        self.assertContains(response, f"Unassigned manager {self.manager.email}")

    def test_panel_member_list(self):
        self.client.login(username=self.hq.email, password='hq')
        Profile.objects.all().delete()
        p1 = PanelistFactory(panel=self.panelist.panel, year_of_birth=1990, month_of_birth=7, day_of_birth=20)
        p2 = PanelistFactory(panel=self.panelist.panel, year_of_birth=1990, month_of_birth=7, day_of_birth=21)

        url = reverse('hq:panelmember-list')
        url_desc = '%s?order_by=year_of_birth&sort=desc' % url
        response = self.client.get(url_desc)

        qs = response.context_data['object_list']

        self.assertEqual(qs[0], p2)
        self.assertEqual(qs[1], p1)

        url_asc = '%s?order_by=year_of_birth&sort=asc' % url
        response_asc = self.client.get(url_asc)

        qs_asc = response_asc.context_data['object_list']

        self.assertEqual(qs_asc[0], p1)
        self.assertEqual(qs_asc[1], p2)


class BlankSlotTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.hq = HqFactory()
        cls.manager = ManagerFactory()
        cls.pm = PanelistFactory(panel__managers=[cls.manager])

    def setUp(self):
        self.client.login(username=self.hq.email, password='hq')

    def test_blank_slot_create(self):
        """Creating a blank slot"""
        self.assertEqual(BlankSlot.objects.count(), 0)
        self.client.post(reverse('hq:blankslot-create'), {
            'name': 'new',
            'description': 'new_description'
        })
        self.assertEqual(BlankSlot.objects.filter(name='new').count(), 1)

    def test_blank_slot_update(self):
        bk = BlankSlot.objects.create(name='name', description='blank_slot_description')
        url = reverse('hq:blankslot-update', args=[bk.pk])
        response = self.client.post(url, {
            'description': "new_description",
        }, follow=True)
        self.assertRedirects(response, reverse('hq:blankslot-list'))
        self.assertContains(response, "Updated")
        bk.refresh_from_db()
        self.assertEqual(bk.description, 'new_description')

    def test_blank_slot_delete(self):
        bs = BlankSlot.objects.create(name='name', description='description')
        profile = Profile.objects.first()
        BlankSlotValue.objects.create(blankslot=bs, profile=profile, value='value')
        url = reverse('hq:blankslot-delete', args=[bs.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please confirm")

        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Deleted blank slot")
        self.assertQuerysetEqual(BlankSlot.objects.all(), [])
        self.assertQuerysetEqual(BlankSlotValue.objects.all(), [])

    def test_csv_export(self):
        bs1 = BlankSlot.objects.create(
            name='blankslot1',
            description='description1',
        )

        BlankSlotValue.objects.create(
            blankslot=bs1,
            profile=Profile.objects.get(email=self.pm.email),
            value="value1"
        )

        response = self.client.get(reverse('hq:blank-slot-export'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "blankslot1")
        self.assertContains(response, "value1")


@modify_settings(MIDDLEWARE={'remove': 'qxsms.middleware.AuthorizationMiddleware'})
class BlankSlotValueUpdateTestCase(TransactionTestCase):

    def setUp(self):
        self.profile = PanelistFactory()

    def test_redirect(self):
        url = reverse('hq:blankslotvalue-update', args=[self.profile.pk])
        response = self.client.post(url, data={
            'form-TOTAL_FORMS': 0,
            'form-INITIAL_FORMS': 0,
            'form-MAX_NUM_FORMS': 1000
        })
        success_url = reverse('hq:blankslotvalue-list', args=[self.profile.pk])
        self.assertRedirects(response, success_url)

    def test_create_duplicate(self):
        url = reverse('hq:blankslotvalue-update', args=[self.profile.pk])
        bk = BlankSlot.objects.create(name='blank_slot_name', description='blank_slot_description')
        response = self.client.post(url, data={
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '',
            'form-0-value': 'new_value',
            'form-0-blankslot': bk.pk,
            'form-1-value': 'new_value',
            'form-1-blankslot': bk.pk,
        })
        self.assertFormsetError(response, 'formset', None, None, 'Cannot assign multiple values to the same variable')


class BlankSlotImportCSVTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.hq = HqFactory()
        cls.manager = ManagerFactory()
        cls.pm = PanelistFactory(panel__managers=[cls.manager])
        bk = BlankSlot.objects.create(
            name='blankslot1',
            description='description1',
        )

        BlankSlotValue.objects.create(
            blankslot=bk,
            profile=Profile.objects.get(email=cls.pm.email)
        )

    def setUp(self):
        self.client.login(username=self.hq.email, password='hq')

    def test_csv_invalid_import(self):
        # Import with wrong blank slot name
        content = "idno,cntry,addvar,value\n{},{},blankslot,new_value".format(self.pm.ess_id, self.pm.country)
        file = SimpleUploadedFile.from_dict(dict(
            filename="file.csv",
            content=bytes(content, 'utf8'),
            content_type='text/csv'
        )
        )
        url = resolve_url('hq:blank-slot-import')
        response = self.client.post(url, {'dataset': file}, format='multipart')
        self.assertContains(response, 'Something went awry. No data was imported.')

    def test_csv_valid_import(self):
        content = "idno,cntry,addvar,value\n{},{},blankslot1,new_value".format(self.pm.ess_id, self.pm.country)
        file = SimpleUploadedFile.from_dict(dict(
            filename="file.csv",
            content=bytes(content, 'utf8'),
            content_type='text/csv'
        )
        )
        url = resolve_url('hq:blank-slot-import')
        response = self.client.post(url, {'dataset': file}, format='multipart', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 additional variables updated')
        self.assertEqual(BlankSlotValue.objects.all()[0].value, "new_value")

    def test_csv_empty_import(self):
        # Import with no data
        file = SimpleUploadedFile.from_dict(dict(
            filename="file.csv",
            content=b'idno,cntry,addvar,value',
            content_type='text/csv')
        )
        url = resolve_url('hq:blank-slot-import')
        response = self.client.post(url, {'dataset': file}, format='multipart')
        self.assertEqual(response.status_code, 302)

    def test_create_blank_slot_value_import_CSV(self):
        nb_bkv = BlankSlotValue.objects.all().count()
        BlankSlot.objects.create(name='blankslot2', description="description2")
        content = "idno,cntry,addvar,value\n{},{},blankslot2,new_value".format(self.pm.ess_id, self.pm.country)
        file = SimpleUploadedFile.from_dict(dict(
            filename="file.csv",
            content=bytes(content, 'utf8'),
            content_type='text/csv'
        )
        )
        url = resolve_url('hq:blank-slot-import')
        response = self.client.post(url, {'dataset': file}, format='multipart', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 additional variables created')
        self.assertEqual(BlankSlotValue.objects.all().count(), nb_bkv + 1)


class ExportCSVPanelistsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hq = HqFactory()
        cls.manager = ManagerFactory()
        cls.pm = PanelistFactory(panel__managers=[cls.manager])

    def test_csv_export(self):
        self.client.login(username=self.hq.email, password='hq')
        response = self.client.get(reverse('hq:panelist-export'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pm.country)
        self.assertContains(response, self.pm.panel.name)

        header, other = response.content.decode(response.charset).split("\r\n", 1)
        fields = header.split(",")
        self.assertIn('panel', fields)


class MessageTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hq = HqFactory()
        cls.manager = ManagerFactory()
        cls.pm = PanelistFactory(panel__managers=[cls.manager])

    @patch('hq.views.services.get_messages')
    def test_messages_list(self, get_messages):
        get_messages.return_value = [
            {'id': 'MS_bOXDEEI0TgbFavQ',
             'description': 'Accueil tutorial',
             'category': 'invite'},
            {'id': 'MS_d4Nmt7qbFlyKEzs',
             'description': 'New Message',
             'category': 'emailSubject'},
            {'id': 'MS_0w9DkEYTMYs8RQq',
             'description': 'test sms',
             'category': 'smsInvite'}
        ]

        self.client.login(username=self.hq.email, password='hq')
        response = self.client.get(reverse('hq:message-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_messages.call_count, 1)
        self.assertContains(response, "<td>Accueil tutorial</td>")


class HqProfileUpdateTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.hq = HqFactory()

    def setUp(self):
        self.client.login(username=self.hq.email, password='hq')

    def test_get_object(self):
        response = self.client.get(reverse('hq:profile-update'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'].email, self.hq.email)


class CreateManagerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = ManagerFactory()
        cls.hq = HqFactory()

    def setUp(self):
        self.client.login(username=self.hq.email, password='hq')

    def test_form_valid(self):
        manager_group = Group.objects.get(name='Managers')
        nb_manager = User.objects.filter(groups=manager_group).count()
        url = resolve_url('hq:manager-create')
        response = self.client.post(url, {
            'email': 'new_manager@qxsms.com',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(groups=manager_group).count(), nb_manager + 1)


class MessageDistributionDetailTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hq = HqFactory()
        cls.m_1 = ManagerFactory()
        cls.pm_1 = PanelistFactory(panel__managers=[cls.m_1])
        cls.link_distribution_1 = LinkDistributionFactory(panels=[cls.pm_1.panel], create_links=True)
        cls.message_distribution_1 = MessageDistributionFactory(link_distribution=cls.link_distribution_1,
                                                                links=cls.link_distribution_1.links.all(),
                                                                contact_mode=MessageDistribution.MODE_SMS)

        cls.message_distribution_2 = MessageDistributionFactory(link_distribution=cls.link_distribution_1,
                                                                links=cls.link_distribution_1.links.all(),
                                                                contact_mode=MessageDistribution.MODE_SMS,
                                                                fallback_of=cls.message_distribution_1)

    def setUp(self):
        self.client.login(username=self.hq.email, password='hq')

    def test_acces_fallback_detail_page(self):
        url = resolve_url('hq:msg-distribution-detail', pk=self.message_distribution_2.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
