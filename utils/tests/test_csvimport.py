# -- STDLIB
from unittest.mock import Mock

# -- DJANGO
from django.conf import settings
from django.contrib.auth.models import Group
from django.test import SimpleTestCase, TestCase

# -- THIRDPARTY
import tablib
from import_export import results

# -- QXSMS
from hq.models import Panel
from panelist.models import Profile
from utils.csvimport import IsNotBlankField, ProfileResource, UpperCaseWidget


class IsNotBlankFieldTestCase(SimpleTestCase):

    def test_blank_value(self):
        f = IsNotBlankField(attribute="email")
        obj = Mock()
        obj.email = ""
        self.assertEqual(f.export(obj), "0")
        obj.email = None
        self.assertEqual(f.export(obj), "0")

    def test_not_blank_value(self):
        f = IsNotBlankField(attribute="email")
        obj = Mock()
        obj.email = "foo@bar.com"
        self.assertEqual(f.export(obj), "1")


class UpperCaseWidgetTestCase(SimpleTestCase):
    def test_clean(self):
        w = UpperCaseWidget()
        self.assertEqual(w.clean("fr "), "FR")

    def test_clean_none(self):
        w = UpperCaseWidget()
        self.assertIsNone(w.clean(None))


class CsvImportTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        Group.objects.create(name=settings.QXSMS_GROUP_PANEL_MEMBERS)
        cls.panel = Panel.objects.create(name='Test Import')

    def test_import_no_rows(self):
        resource = ProfileResource(panel_id=self.panel.pk)
        dataset = tablib.Dataset(headers=resource.get_user_visible_headers())
        result = resource.import_data(dataset)
        self.assertFalse(result.has_errors())
        self.assertFalse(any(result.totals.values()))

    def test_invalid_panel(self):
        pass

    def test_unique_together_works(self):
        """It is not an error to have profiles with the same ESS ID in two different panels."""
        other_panel = Panel.objects.create(name='Other')
        Profile.objects.create(
            ess_id=1,
            panel=other_panel,
            first_name='a',
            last_name='A',
            sex=1,
            email='a@a.fr',
            country='FR',
            language='ENG',
            internet_use=1,
            day_of_birth=1,
            month_of_birth=1,
            year_of_birth=2000,
            education_years=0,
        )
        imported_profile = dict(
            ess_id=1,
            first_name='b',
            last_name='B',
            sex=1,
            email='b@b.fr',
            country='FR',
            language='ENG',
            internet_use=1,
            day_of_birth=1,
            month_of_birth=1,
            year_of_birth=2000,
            education_years=0,
        )
        headers = list(imported_profile)
        row = imported_profile.values()
        data = tablib.Dataset(row, headers=headers)
        resource = ProfileResource(panel_id=self.panel.pk)
        result = resource.import_data(data, raise_errors=True)
        self.assertFalse(result.has_errors())
        self.assertEqual(Profile.objects.filter(ess_id=1).count(), 2)

    def test_import_types(self):
        """Valid import with 1 creation, 1 update and 1 skip."""
        to_update = dict(
            ess_id=1,
            first_name='a',
            last_name='A',
            sex=1,
            email='a@a.fr',
            country='FR',
            language='ENG',
            internet_use=1,
            day_of_birth=1,
            month_of_birth=1,
            year_of_birth=2000,
            education_years=0,
        )
        Profile.objects.create(panel=self.panel, **to_update)
        to_update['year_of_birth'] = 2001
        update_row = [str(v) for v in to_update.values()]

        to_skip = dict(
            ess_id=3,
            first_name='c',
            last_name='C',
            sex=1,
            email='c@c.fr',
            country='FR',
            language='ENG',
            internet_use=1,
            day_of_birth=1,
            month_of_birth=1,
            year_of_birth=2000,
            education_years=0,
        )
        Profile.objects.create(panel=self.panel, **to_skip)
        skip_row = [str(v) for v in to_skip.values()]

        to_create = dict(
            ess_id=2,
            first_name='b',
            last_name='B',
            sex=1,
            email='b@b.fr',
            country='FR',
            language='ENG',
            internet_use=1,
            day_of_birth=1,
            month_of_birth=1,
            year_of_birth=2000,
            education_years=0,
        )
        create_row = [str(v) for v in to_create.values()]

        headers = list(to_create)
        data = tablib.Dataset(create_row, skip_row, update_row, headers=headers)
        resource = ProfileResource(panel_id=self.panel.pk)
        result = resource.import_data(data)
        self.assertFalse(result.has_errors())
        self.assertEqual(result.totals[results.RowResult.IMPORT_TYPE_UPDATE], 1)
        self.assertEqual(result.totals[results.RowResult.IMPORT_TYPE_SKIP], 1)
        self.assertEqual(result.totals[results.RowResult.IMPORT_TYPE_NEW], 1)
        self.assertEqual(self.panel.profile_set.count(), 3)

    def test_last_update_is_applied(self):
        """If several rows refer to an ess_id, the last one applies"""
        attrs = dict(
            ess_id=1,
            first_name='a',
            last_name='A',
            sex=1,
            email='a@a.fr',
            country='FR',
            language='ENG',
            internet_use=1,
            day_of_birth=1,
            month_of_birth=1,
            year_of_birth=2000,
            education_years=0,
        )
        p = Profile.objects.create(panel=self.panel, **attrs)
        attrs['first_name'] = 'foo'
        u1 = [str(v) for v in attrs.values()]
        attrs['first_name'] = 'bar'
        u2 = [str(v) for v in attrs.values()]
        data = tablib.Dataset(u1, u2, headers=list(attrs))
        resource = ProfileResource(panel_id=self.panel.pk)
        result = resource.import_data(data)
        self.assertFalse(result.has_errors())
        self.assertEqual(result.totals[results.RowResult.IMPORT_TYPE_UPDATE], 2)
        p.refresh_from_db()
        self.assertEqual(p.first_name, 'bar')

    def test_required(self):  # FIXME: if we remove fields from the list it can still pass
        """All fields except `not_required_fields` are required at import"""
        not_required_fields = [
            'address',
            'is_opt_out',
            'opt_out_date',
            'opt_out_reason',
            'delete_contact_data',
            'delete_survey_data',
            'out_of_country',
            'no_incentive',
            'no_letter',
            'no_text',
            'no_email',
        ]
        resource = ProfileResource(panel_id=self.panel.pk)
        headers = resource.get_user_visible_headers()
        row = [''] * len(headers)
        data = tablib.Dataset(row, headers=headers)
        result = resource.import_data(data)
        errors = result.invalid_rows[0].error.message_dict
        for field in not_required_fields:
            self.assertFalse(any(('required' in msg) for msg in errors.get(field, [])))

    def test_cleaned_data(self):
        """Whitespaces are stripped"""

        valid_row = {
            'ess_id': '1',
            'first_name': 'a',
            'last_name': 'A',
            'email': 'a@a.fr',
            'sex': '1',
            'day_of_birth': '01',
            'month_of_birth': '12',
            'year_of_birth': '2000',
            'education_years': '0',
            'country': 'FR ',
            'language': 'eng',
            'internet_use': '1',

        }

        cleaned_row = {
            'ess_id': 1,
            'first_name': 'a',
            'last_name': 'A',
            'email': 'a@a.fr',
            'sex': 1,
            'day_of_birth': 1,
            'month_of_birth': 12,
            'year_of_birth': 2000,
            'education_years': 0,
            'country': 'FR',
            'language': 'ENG',
            'internet_use': 1,

        }
        headers = list(valid_row)
        data = tablib.Dataset(valid_row.values(), headers=headers)
        resource = ProfileResource(panel_id=self.panel.pk)
        result = resource.import_data(data, raise_errors=True)
        self.assertFalse(result.invalid_rows)
        p = Profile.objects.filter(ess_id=1).values(*headers).first()
        self.assertDictEqual(p, cleaned_row)

    def test_cleaned_language(self):

        valid_row = {
            'ess_id': '1',
            'first_name': 'a',
            'last_name': 'A',
            'email': 'a@a.fr',
            'sex': '1',
            'day_of_birth': '01',
            'month_of_birth': '12',
            'year_of_birth': '2000',
            'education_years': '0',
            'country': 'FR ',
            'language': 'en',
            'internet_use': '1',
        }

        headers = list(valid_row)
        data = tablib.Dataset(valid_row.values(), headers=headers)
        resource = ProfileResource(panel_id=self.panel.pk)
        result = resource.import_data(data, raise_errors=True)
        self.assertFalse(result.invalid_rows)
        p = Profile.objects.get(ess_id=1)
        self.assertEquals(p.language, "EN")

    def test_import_multiple_blank_emails(self):
        row1 = dict(
            ess_id=1,
            sex=1,
            email='',
            phone='+33666666666',
            country='FR',
            language='ENG',
            internet_use=1,
            day_of_birth=1,
            month_of_birth=1,
            year_of_birth=2000,
            education_years=0,
        )
        row2 = dict(
            ess_id=2,
            sex=1,
            email='',
            phone='+33555555555',
            country='FR',
            language='ENG',
            internet_use=1,
            day_of_birth=1,
            month_of_birth=1,
            year_of_birth=2000,
            education_years=0,
        )
        headers = list(row1)
        data = tablib.Dataset(row1.values(), row2.values(), headers=headers)
        resource = ProfileResource(panel_id=self.panel.pk)
        result = resource.import_data(data, raise_errors=True)
        self.assertFalse(result.has_errors())
        self.assertFalse(result.invalid_rows)


class CSVExportTestCase(TestCase):
    def test_export(self):
        p = Profile(language="EN", email="foo@bar.uk", phone="")
        r = ProfileResource()
        dataset = r.export(queryset=[p], fields=['language', 'email', 'email_not_blank', 'phone', 'phone_not_blank'])
        expected = {"email": "foo@bar.uk", "mobile": "", "lng": "EN", "emailpres": "1", "mobilepres": "0"}
        row, = dataset.dict
        self.assertDictEqual(dict(row), expected)
