# -- QXSMS
from panelist.models import AbstractProfile

MISSING_CODES = {
    "en-gb": "gb",
    "cs": "cz",
    "sl": "si",
    "sv": "se",
}

DICT_COUNTRIES = dict(AbstractProfile.COUNTRIES)


def lng_to_country(lng):
    return DICT_COUNTRIES[MISSING_CODES[lng].upper() if lng in MISSING_CODES else lng.upper()]
