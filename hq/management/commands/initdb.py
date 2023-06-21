
# -- DJANGO
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

# -- QXSMS
from qxsms.settings import (
    QXSMS_GROUP_ADMINS, QXSMS_GROUP_MANAGERS, QXSMS_GROUP_PANEL_MEMBERS,
)

User = get_user_model()


def init_qxsms():
    group_names = [QXSMS_GROUP_ADMINS, QXSMS_GROUP_PANEL_MEMBERS, QXSMS_GROUP_MANAGERS]
    Group.objects.bulk_create(Group(name=name) for name in group_names)
    admin = User.objects.create_superuser(email="hq@qxsms.org", password="hq")
    admin.groups.add(Group.objects.get(name=QXSMS_GROUP_ADMINS))


def revert_init():
    Group.objects.all().delete()
    User.objects.all().delete()


class Command(BaseCommand):
    help = 'Init database (default) or revert with --revert argument'

    def add_arguments(self, parser):
        parser.add_argument('-r', '--reset', help="Revert the initialization script.", action='store_true')

    def handle(self, *args, **kwargs):
        reset = kwargs.get('reset')
        if reset:
            revert_init()
        else:
            init_qxsms()
