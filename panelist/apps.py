# -- DJANGO
from django.apps import AppConfig
from django.db.models.signals import post_delete


class PanelistConfig(AppConfig):
    name = 'panelist'

    def ready(self):
        # -- QXSMS
        from panelist.models import Profile
        from panelist.signals import post_delete_profile

        post_delete.connect(post_delete_profile, sender=Profile)
