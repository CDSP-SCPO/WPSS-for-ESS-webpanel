# -- DJANGO
from django.core.management.base import BaseCommand

# -- QXSMS
from panelist.models import Profile


class Command(BaseCommand):
    help = "Get panelist IDs from a list of Profile.uid (extRef on Qualtrics side)"

    def add_arguments(self, parser):
        parser.add_argument('list', nargs='+', help='the list of contact IDs')

    def handle(self, *args, **options):
        profile_list = Profile.objects.filter(uid__in=options['list'])
        ids = [profile.panelist_id for profile in profile_list]
        self.stdout.write(self.style.SUCCESS("\n".join(ids)))
