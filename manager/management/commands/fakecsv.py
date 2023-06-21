# -- DJANGO
from django.core.management import BaseCommand, CommandError

# -- QXSMS
from panelist.factories import PanelistFactory
from utils.csvimport import ProfileResource


class Command(BaseCommand):
    help = 'Generate fake profile CSV data'

    def add_arguments(self, parser):
        parser.add_argument('-n', '--nb-rows', type=int, default=100, help='Number of rows')
        parser.add_argument('-o', '--output', type=str, help='Save output under given file name')
        # By default, readonly fields are excluded since we most likely want to import back what we generate
        parser.add_argument('-r', '--include-readonly', action='store_true', help='Include readonly columns')

    def handle(self, *args, **options):
        nb_rows = options['nb_rows']
        file = options['output']
        include_readonly = options['include_readonly']

        profiles = PanelistFactory.build_batch(nb_rows, panel=None)
        resource = ProfileResource(panel_id=None)
        dataset = resource.export(exclude_readonly=(not include_readonly), queryset=profiles)

        if file:
            try:
                with open(file, 'w') as f:
                    f.write(dataset.csv)
            except IOError:
                raise CommandError(f"Could not write data to file: {file}.")
        else:
            self.stdout.write(dataset.csv)
