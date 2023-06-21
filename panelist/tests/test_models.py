# -- DJANGO
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.utils import datetime_safe

# -- QXSMS
from manager.factories import ManagerFactory
from panelist.factories import PanelistFactory
from panelist.models import BlankSlot, BlankSlotValue, Profile

User = get_user_model()


class BlankSlotTestCase(SimpleTestCase):

    def test_str(self):
        b = BlankSlot(name='foo', description='bar')
        self.assertEqual(str(b), 'foo')


class ProfileTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.nc = ManagerFactory()
        cls.panelist = PanelistFactory(panel__managers=[cls.nc])
        cls.blankslot = BlankSlot.objects.create(name='bk1')
        cls.panel = cls.panelist.panel

    def test_embedded_data(self):
        BlankSlotValue.objects.create(profile=self.panelist, blankslot=self.blankslot, value='test')
        self.assertEqual(self.panelist.get_embedded_data()['bk1'], 'test')

    def test_clean_opt_out(self):
        self.panelist.opt_out_reason = 'reason'
        self.assertRaises(ValidationError, self.panelist.full_clean)

    def test_unique_constraint_ess_id_panel(self):

        profile = Profile(
            ess_id=self.panelist.ess_id,
            panel=self.panel,
        )
        with self.assertRaisesMessage(ValidationError, "Profile with this Panel and Ess id already exists."):
            profile.validate_unique()

    def test_unique_constraints_on_related_user(self):
        User.objects.create(email='foo@bar.eu')
        User.objects.create(phone='+33666666666')
        profile = Profile(email='foo@bar.eu')
        with self.assertRaisesMessage(ValidationError, "Email belongs to another user"):
            profile.validate_unique()
        profile = Profile(phone='+33666666666')
        with self.assertRaisesMessage(ValidationError, "Phone belongs to another user"):
            profile.validate_unique()

    def test_validate_eduyrs_range(self):
        profile = Profile(education_years=100)
        with self.assertRaisesMessage(ValidationError, "Must be between 1 and 99."):
            profile.full_clean()

    def test_validate_dob_range(self):
        profile = Profile(day_of_birth=50)
        with self.assertRaisesMessage(ValidationError, "Must be between 1 and 31, or 77, 88, 99."):
            profile.full_clean()

    def test_validate_mob_range(self):
        profile = Profile(month_of_birth=13)
        with self.assertRaisesMessage(ValidationError, "Must be between 1 and 12, or 77, 88, 99."):
            profile.full_clean()

    def test_validate_yob_range(self):
        profile = Profile(year_of_birth=2010)
        with self.assertRaisesMessage(ValidationError, "Must be between 1900 and 2005, or 7777, 8888, 9999."):
            profile.full_clean()

    def test_date_of_birth(self):
        # All field are good
        with self.subTest():
            profile = Profile(year_of_birth=1993, month_of_birth=10, day_of_birth=23)
            self.assertEqual(profile.date_of_birth, datetime_safe.date(year=1993, month=10, day=23))
        # Year above 7777
        with self.subTest():
            profile = Profile(year_of_birth=8888, month_of_birth=42, day_of_birth=11)
            self.assertEqual(profile.date_of_birth, None)
        # Month and day above 77
        with self.subTest():
            profile = Profile(year_of_birth=1993, month_of_birth=77, day_of_birth=77)
            self.assertEqual(profile.date_of_birth, datetime_safe.date(year=1993, month=1, day=1))
        # Month above 12 (simulation of the bug)
        with self.subTest():
            profile = Profile(year_of_birth=1993, month_of_birth=27, day_of_birth=11)
            with self.assertRaisesMessage(ValueError, "month must be in 1..12"):
                profile.date_of_birth
