# -- STDLIB
import random
from collections import defaultdict

# -- THIRDPARTY
import factory
import phonenumbers
from faker import Faker
from faker.config import AVAILABLE_LOCALES
from faker.providers import BaseProvider

# -- QXSMS (LOCAL)
from .models import Profile

COUNTRY_CHOICES = [country[0] for country in Profile.COUNTRIES]


COUNTRY_LOCALES = defaultdict(list)
for lang, countries in BaseProvider.language_locale_codes.items():
    for country in countries:
        if f"{lang}_{country}" in AVAILABLE_LOCALES:
            COUNTRY_LOCALES[country].append(f"{lang}_{country}")


def random_phone_number(p):
    if COUNTRY_LOCALES[p.country]:
        loc = random.choice(COUNTRY_LOCALES[p.country])
    else:
        loc = f"{p.country.lower()}_{p.country.upper()}"

    try:
        f = Faker(locale=loc)
        country = p.country
    except AttributeError:  # default locale if Faker is not able to generate for asked locale.
        f = Faker(locale="fr_FR")
        country = "FR"

    while True:
        try:
            pn = phonenumbers.parse(f.phone_number(), country)
        except phonenumbers.phonenumberutil.NumberParseException:
            # sometime Faker will generate incorrect phone number for the country...
            continue
        if phonenumbers.is_valid_number(pn):
            phone = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164)
            break

    return phone


class PanelistFactory(factory.django.DjangoModelFactory):
    '''
    A manager must be created before calling PanelistFactory

    Each time PanelistFactory is called, a panel is created unless an existing panel is passed as a parameter
    to PanelistFactory.
    In this way the created panel has no manager, so the manager of the panel must be specified when calling
    PanelistFactory.

    Example:
        manager = ManagerFactory()               ==> Create a NC

        p1 = PanelistFactory(panel__managers=[manager]) ==> Create a panelist
                                                     Create a panel
                                                     Add the panelist to the panel
                                                     Add the manager as the panel manager

        p2 = PanelistFactory(panel=p1.panel)     ==> Create a panelist
                                                     Add p2 to the same panel as p1 which has already a manager


    '''
    class Meta:
        model = Profile

    ess_id = factory.Sequence(lambda n: n)
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    internet_use = factory.Iterator(Profile.INTERNET_USES, getter=lambda c: c[0])
    sex = factory.Iterator(Profile.SEXES, getter=lambda c: c[0])
    email = factory.Sequence(lambda n: 'panelist_{}@qxsms.com'.format(n))
    year_of_birth = factory.Faker('random_int', min=1970, max=2000)
    day_of_birth = factory.Faker('random_int', min=1, max=28)
    month_of_birth = factory.Faker('random_int', min=1, max=12)
    education_years = factory.Faker('random_int', min=0, max=7)
    panel = factory.SubFactory('hq.factories.PanelFactory')
    country = factory.LazyFunction(lambda: random.choice(COUNTRY_CHOICES))
    phone = factory.LazyAttribute(random_phone_number)
    language = 'fr'

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if self.user:
            self.user.set_password('pm')
            self.user.save()
