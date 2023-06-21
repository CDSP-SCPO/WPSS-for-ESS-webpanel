# -- STDLIB
import logging

# -- DJANGO
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.utils import translation

logger = logging.getLogger('django.server')


class AuthorizationMiddleware:

    APP_GROUPS = {
        'panelist': settings.QXSMS_GROUP_PANEL_MEMBERS,
        'hq': settings.QXSMS_GROUP_ADMINS,
        'manager': settings.QXSMS_GROUP_MANAGERS
    }

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):

        match = request.resolver_match

        if match.app_name not in self.APP_GROUPS:
            return None

        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        group_name = self.APP_GROUPS[match.app_name]
        if not request.user.groups.filter(name=group_name).exists():
            raise PermissionDenied


class ForceEnglishMiddleware:
    """Activate English language for 'hq' and 'manager' URL namespaces.

    Do nothing for if the current language is already set to English.
    Otherwise, set the current language to english and record this preference in the user's session so that
    LocaleMiddleware will activate English for us in following requests.
    """

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        lang = translation.get_language()
        if lang != settings.LANGUAGE_CODE and match.app_name in ['hq', 'manager']:
            translation.activate(settings.LANGUAGE_CODE)
            request.LANGUAGE_CODE = request.session[translation.LANGUAGE_SESSION_KEY] = translation.get_language()
