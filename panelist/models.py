# -- STDLIB
import logging
import uuid

# -- DJANGO
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator, MinValueValidator, RegexValidator,
)
from django.db import models, transaction
from django.utils import datetime_safe, timezone
from django.utils.translation import gettext_lazy as _

# -- THIRDPARTY
from dateutil.relativedelta import relativedelta
from phonenumber_field.modelfields import PhoneNumberField

# -- QXSMS
from hq.models import Panel

User = get_user_model()
logger = logging.getLogger(__name__)


def validate_eduyrs_range(value):
    if not 0 <= value <= 99:
        # Translators: ignore
        raise ValidationError(_('Must be between 1 and 99.'))


def validate_dob_range(value):
    if not ((1 <= value <= 31) or value in [77, 88, 99]):
        # Translators: ignore
        raise ValidationError(_('Must be between 1 and 31, or 77, 88, 99.'))


def validate_mob_range(value):
    if not ((1 <= value <= 12) or value in [77, 88, 99]):
        # Translators: ignore
        raise ValidationError(_('Must be between 1 and 12, or 77, 88, 99.'))


def validate_yob_range(value):
    if not ((1900 <= value <= 2005) or value in [7777, 8888, 9999]):
        # Translators: ignore
        raise ValidationError(_('Must be between 1900 and 2005, or 7777, 8888, 9999.'))


BLANK_SLOT_NAME_REGEX = RegexValidator(r'^[A-Za-z0-9]*$', 'Only numbers and letters are accepted.')


class AbstractProfile(models.Model):
    class Meta:
        abstract = True

    FIELD_MAP = (
        ('uid', 'extRef', lambda x: x.hex),
        ('first_name', 'firstName', None),
        ('last_name', 'lastName', None),
        ('email', 'email', None),
        ('language', 'language', None),
        ('is_opt_out', 'unsubscribed', None),
        ('phone', 'phone', lambda x: str(x)[1:]),  # Remove the + before the phone number for Qualtrics
    )

    COUNTRIES = [
        ('AT', _('Austria')),
        ('BE', _('Belgium')),
        ('BG', _('Bulgaria')),
        ('CZ', _('Czechia')),
        ('HR', _('Croatia')),
        ('CY', _('Cyprus')),
        ('EE', _('Estonia')),
        ('FI', _('Finland')),
        ('FR', _('France')),
        ('DE', _('Germany')),
        ('HU', _('Hungary')),
        ('IS', _('Iceland')),
        ('IE', _('Ireland')),
        ('IT', _('Italy')),
        ('LV', _('Latvia')),
        ('LT', _('Lithuania')),
        ('NL', _('The Netherlands')),
        ('NO', _('Norway')),
        ('PL', _('Poland')),
        ('PT', _('Portugal')),
        ('SK', _('Slovakia')),
        ('SI', _('Slovenia')),
        ('SE', _('Sweden')),
        ('GB', _('United Kingdom')),
        ('CH', _('Switzerland')),
        ('AL', _('Albania')),
        ('DK', _('Denmark')),
        ('IL', _('Israel')),
        ('ME', _('Montenegro')),
        ('RS', _('Serbia')),
        ('ES', _('Spain')),
        ('GR', _('Greece')),
        ('XK', _('Kosovo')),
        ('LU', _('Luxembourg')),
        ('RO', _('Romania')),
        ('RU', _('Russia')),
        ('TK', _('Turkey')),
        ('UA', _('Ukraine')),
    ]

    ACCOUNT_NOTACTIVATED = 0
    ACCOUNT_ACTIVATED = 1
    ACCOUNT_DEACTIVATED = 2
    ACCOUNT_OPTEDOUT = 3

    STATE_LABELS = {
        # Translators: ignore
        ACCOUNT_NOTACTIVATED: (_('Never logged in'), 'bg-warning'),
        # Translators: ignore
        ACCOUNT_ACTIVATED: (_('Has logged in'), 'bg-success'),
        # Translators: ignore
        ACCOUNT_DEACTIVATED: (_('Deactivated'), 'bg-danger'),
        # Translators: ignore
        ACCOUNT_OPTEDOUT: (_('Opted out'), 'bg-secondary'),
    }

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    panel = models.ForeignKey(Panel, on_delete=models.CASCADE)
    first_name = models.CharField(_('first name'), max_length=256, blank=True)
    last_name = models.CharField(_('last name'), max_length=256, blank=True)
    email = models.EmailField(
        _('email address'),
        blank=True,
        null=True,
        unique=True,
        error_messages={
            'unique': _("A user with that email address already exists."),
        }
    )
    temp_email = models.EmailField(
        blank=True,
        null=True,
        unique=True
    )
    temp_email_expiry = models.DateTimeField(
        blank=True,
        null=True,
    )
    phone = PhoneNumberField(
        _('phone number'),
        blank=True,
        null=True,
        unique=True,
        error_messages={
            'unique': _("A user with that phone number already exists."),
        }
    )
    temp_phone = PhoneNumberField(blank=True, null=True, unique=True)
    temp_phone_expiry = models.DateTimeField(blank=True, null=True)

    is_opt_out = models.BooleanField(default=False)

    language = models.CharField(verbose_name=_('language'), max_length=10, default='')

    address_property_name = models.CharField(verbose_name=_('name of property'), blank=True, null=True, max_length=50)
    address_number = models.CharField(verbose_name=_('number'), blank=True, null=True, max_length=50)
    address = models.CharField(verbose_name=_('address line 1'), blank=True, null=True, max_length=50)
    address2 = models.CharField(verbose_name=_('address line 2'), blank=True, null=True, max_length=50)
    city = models.CharField(verbose_name=_('city'), blank=True, null=True, max_length=50)
    county = models.CharField(verbose_name=_('county'), blank=True, null=True, max_length=50)
    postcode = models.CharField(verbose_name=_('postcode'), blank=True, null=True, max_length=50)
    country = models.CharField(verbose_name=_('country'), max_length=2, choices=COUNTRIES)

    day_of_birth = models.PositiveIntegerField(verbose_name=_('day of birth'), validators=[validate_dob_range])
    month_of_birth = models.PositiveIntegerField(verbose_name=_('month of birth'), validators=[validate_mob_range])
    year_of_birth = models.PositiveIntegerField(verbose_name=_('year of birth'), validators=[validate_yob_range])

    def __str__(self):
        return f'{self.last_name.upper()} {self.first_name.capitalize()}'

    @property
    def temp_email_is_valid(self):
        return self.temp_email_expiry and timezone.now() < self.temp_email_expiry

    @property
    def username(self):
        return self.user.get_username()

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"

    @property
    def is_active(self):
        raise NotImplementedError()

    @property
    def account_state(self):

        if not self.is_active:
            return self.ACCOUNT_DEACTIVATED

        if self.is_opt_out:
            return self.ACCOUNT_OPTEDOUT

        if self.user.last_login:
            return self.ACCOUNT_ACTIVATED

        return self.ACCOUNT_NOTACTIVATED

    @property
    def state_label(self):
        return self.STATE_LABELS[self.account_state]

    @property
    def email_label(self):
        return (self.email, ('text-warning' if self.temp_email_is_valid else None))

    @property
    def date_of_birth(self):
        if self.year_of_birth:
            day = self.day_of_birth or 1
            month = self.month_of_birth or 1
            return datetime_safe.date(self.year_of_birth, month, day)
        else:
            return None

    @property
    def age(self):
        try:
            today = timezone.now().date()
            return relativedelta(today, self.date_of_birth).years
        except Exception:
            return None

    def save(self, *args, **kwargs):
        # Change from blank strings to None so that we don't have uniqueness problems between profiles.
        self.email = self.email or None
        self.phone = self.phone or None
        if self.user_id is None and self.pk is None:
            # Instance is being created and user not created
            with transaction.atomic():
                self.user = User.objects.create_user(
                    User.objects.make_random_password(),
                    email=self.email,
                    first_name=self.first_name,
                    last_name=self.last_name,
                    phone=self.phone,
                    is_active=self.is_active,
                )
                self.user.groups.add(Group.objects.get_or_create(name=settings.QXSMS_GROUP_PANEL_MEMBERS)[0])
        elif self.user_id:
            # User already exists
            fields_to_update = {
                'first_name': self.first_name,
                'last_name': self.last_name,
                'email': self.email,
                'phone': self.phone,
                'is_active': self.is_active,
            }
            User.objects.filter(id=self.user_id).update(**fields_to_update)

        return super().save(*args, **kwargs)


class Profile(AbstractProfile):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['panel', 'ess_id'], name='unique_panelist'),
        ]

    SEXES = [
        (1, _('Male')),
        (2, _('Female')),
        (3, _('Other')),
        (7, _('Refusal')),
        (8, _('Don\'t know')),
        (9, _('No answer')),
    ]

    INTERNET_USES = [
        (1, _('Never')),
        (2, _('Only occasionally')),
        (3, _('A few times a week')),
        (4, _('Most days')),
        (5, _('Every day')),
        (7, _('Refusal')),
        (8, _('Don\'t know')),
        (9, _('No answer')),
    ]

    AGE_GROUPS = (
        ('18-24', {'min': 18, 'max': 24, 'code': 1}),
        ('25-34', {'min': 25, 'max': 34, 'code': 2}),
        ('35-44', {'min': 35, 'max': 44, 'code': 3}),
        ('45-54', {'min': 45, 'max': 54, 'code': 4}),
        ('55-64', {'min': 55, 'max': 64, 'code': 5}),
        ('65-74', {'min': 65, 'max': 74, 'code': 6}),
        ('75+', {'min': 75, 'max': None, 'code': 7}),
        (_("Not available"), {'min': None, 'max': None, 'code': 9}),
    )

    sex = models.PositiveIntegerField(verbose_name=_('sex'), choices=SEXES)
    internet_use = models.PositiveIntegerField(verbose_name=_('internet use'), choices=INTERNET_USES)
    education_years = models.PositiveIntegerField(
        verbose_name=_('years of education'),
        validators=[validate_eduyrs_range],
    )
    ess_id = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(999999999999)]  # max_length=12
    )

    opt_out_date = models.DateTimeField(blank=True, null=True)
    opt_out_reason = models.TextField(max_length=1000, blank=True)
    delete_contact_data = models.BooleanField(default=False)
    anonymized_since = models.DateTimeField(blank=True, null=True)  # Filled in when a manager disables a profile
    delete_survey_data = models.BooleanField(default=False)
    out_of_country = models.BooleanField(default=False)

    no_incentive = models.BooleanField(default=False)
    no_letter = models.BooleanField(default=False)
    no_text = models.BooleanField(default=False)
    no_email = models.BooleanField(default=False)

    @property
    def panelist_id(self):
        return f'{self.country}{self.ess_id}'

    @property
    def date_of_birth(self):
        if self.year_of_birth < 7777:
            day = self.day_of_birth if self.day_of_birth < 77 else 1
            month = self.month_of_birth if self.month_of_birth < 77 else 1
            return datetime_safe.date(self.year_of_birth, month, day)
        else:
            return None

    @property
    def age_group(self):
        for value, rng in self.AGE_GROUPS:
            rng_min = rng['min']
            rng_max = rng['max']
            if rng_min and rng_min <= self.age:
                if (rng_max and self.age <= rng_max) or not rng_max:
                    return rng['code'], value
        na_value, na_rng = self.AGE_GROUPS[-1]
        return na_rng['code'], na_value

    @property
    def age_group_code(self):
        return self.age_group[0]

    def get_embedded_data(self):
        data = {
            'id': self.panelist_id,
            'ess_id': self.ess_id,
            'sex': self.sex,
            'country': self.country,
            'panel': self.panel.name,
        }

        for name, value in self.blankslotvalue_set.values_list('blankslot__name', 'value'):
            data[name] = value
        return data

    def clean(self):
        if not self.email and not self.phone:
            raise ValidationError({
                # Translators: ignore
                'email': _('Email or phone number required.'),
                # Translators: ignore
                'phone': _('Email or phone number required.')
            })
        if not self.is_opt_out and (self.opt_out_date or self.opt_out_reason):
            # Translators: ignore
            raise ValidationError({'is_opt_out': _('The panelist should be opt out if a date or reason is filled.')})

        return super().clean()

    def full_clean(self, exclude=None, validate_unique=True):
        """Exclude `user` from model validation

        Since these attributes are not set from user-submitted data,
        omit them from validation. This is useful in the import machinery,
        when new instances have both attributes to `None` when they are
        validated, before saving.
        """
        if exclude is None:
            exclude = []
        # Cast to `list` in case we got a `dict_keys` instance.
        exclude = list(exclude) + ['user']
        super().full_clean(exclude=exclude, validate_unique=validate_unique)

    def validate_unique(self, exclude=None):
        """Check that email and phone are not already taken by unrelated User objects"""
        super().validate_unique(exclude=exclude)
        qs = User.objects.all()
        # Exclude our related user, if we are updating
        if self.user is not None:
            qs = qs.exclude(pk=self.user.pk)
        errors = {}
        exclude = exclude or []
        for attr in ("email", "phone"):
            value = getattr(self, attr)
            if attr in exclude or value is None:
                continue
            if qs.filter(**{attr: value}).exists():
                # Translators: ignore
                errors[attr] = [ValidationError(_(f"{attr.capitalize()} belongs to another user."))]
        if errors:
            raise ValidationError(errors)

    def to_json(self):
        """
        Convert a dict of profile attributes to a json-serializable dict as expected
        by the Qualtrics API.

        :return: list of serialized profiles ready to submit to the Qualtrics API
        """

        serialized = {}
        for (field, qx_field, transform) in self.FIELD_MAP:
            value = getattr(self, field)
            if value is None or value == '':
                continue
            if transform:
                value = transform(value)
            serialized[qx_field] = value

        serialized['embeddedData'] = self.get_embedded_data()
        return serialized

    @property
    def anonymized_values(self):
        return {
            "email": f"panelist-{self.country}-{self.ess_id}@opinionsurvey.org",
            "phone": None,
            "first_name": "",
            "last_name": "",
            "address_property_name": "",
            "address_number": "",
            "address": "",
            "address2": "",
            "city": "",
            "county": "",
            "postcode": "",
            "language": "",
            "sex": 9,
            "day_of_birth": 99,
            "month_of_birth": 99,
            "year_of_birth": 9999,
            "education_years": 99,
            "internet_use": 9,
            # Added for consistency
            "is_opt_out": True,
            "delete_contact_data": True,
        }

    def deactivate(self):
        # Anonymize data, profile is set to readonly in the form
        now = timezone.now()
        # If opt out was not already set, add the opt out date
        if not self.is_opt_out and not self.opt_out_date:
            self.opt_out_date = now
        for field, value in self.anonymized_values.items():
            setattr(self, field, value)
        self.user.is_active = False
        self.anonymized_since = now
        self.save()

    @property
    def is_active(self):
        return (not self.anonymized_since)


class BlankSlot(models.Model):
    name = models.CharField(max_length=50, unique=True, validators=[BLANK_SLOT_NAME_REGEX])
    description = models.TextField(max_length=500)

    def __str__(self):
        return self.name


class BlankSlotValue(models.Model):
    class Meta:
        unique_together = ('profile', 'blankslot')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    blankslot = models.ForeignKey(BlankSlot, on_delete=models.CASCADE)
    value = models.CharField(max_length=100, blank=True, default='')
