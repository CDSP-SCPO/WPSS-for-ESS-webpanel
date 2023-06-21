# -- DJANGO
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates objects Hq, Managers and PanelMembers in the table Group"

    def handle(self, *args, **options):
        try:
            Group.objects.get_or_create(name="Hq")
            Group.objects.get_or_create(name="Managers")
            Group.objects.get_or_create(name="PanelMembers")
            self.stdout.write(self.style.SUCCESS("Group Hq, Managers and PanelMembers created"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {e}'))
