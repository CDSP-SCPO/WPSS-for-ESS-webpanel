# -- DJANGO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import BaseCommand, CommandError

# -- QXSMS
from hq.models import Panel
from manager.forms import CSVImportForm
from utils import csvimport as csvi


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('panel_id', type=int)
        parser.add_argument('csv_file', type=str)
        parser.add_argument('--dryrun', action='store_true')

    def handle(self, *args, **options):
        panel_id = options['panel_id']
        csv_file = options['csv_file']
        try:
            panel = Panel.objects.get(pk=panel_id)
            prompt = f"Import file {csv_file} into panel {panel.name}? ([y]/n)"
            confirm = input(prompt)
            while confirm and confirm not in 'yYnN':
                confirm = input(prompt)
            if confirm not in 'yY':
                return
        except Panel.DoesNotExist:
            raise CommandError(f"No panel with id={panel_id}.")

        with open(csv_file, 'rb') as f:
            file = SimpleUploadedFile(f.name, f.read())

        form = CSVImportForm(files={'dataset': file})
        if not form.is_valid():
            raise CommandError(f"Invalid CSV file: {form.errors}")

        dataset = form.cleaned_data['dataset']
        resource = csvi.ProfileResource(panel_id=panel_id)
        result = resource.import_data(dataset, dry_run=True)

        # TODO Error reporting
        if result.has_errors():
            raise CommandError("Global error.")
        if result.has_validation_errors():
            raise CommandError("Invalid rows")

        if not options['dryrun']:
            self.stdout.write("Would now import for real.")

        self.log_results(result)

    def log_results(self, result):
        self.stdout.write(f"Results: {result.totals}")

    def log_errors(self, result):
        pass
