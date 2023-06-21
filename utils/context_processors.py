# -- STDLIB
import os

# -- DJANGO
from django.utils.translation import gettext_lazy as _


def qxsms_version(request):
    return {'QXSMS_VERSION': os.getenv('QXSMS_VERSION', default="dev")}


def instance_name(request):
    name = _("Opinion Study")
    user = request.user
    if hasattr(user, 'profile'):  # if the user is a panelist
        name = get_instance_name(user.profile.get_country_display())

    return {'INSTANCE_NAME': name}


def get_instance_name(country):
    return _("Opinion Study for %(country)s") % {'country': country}
