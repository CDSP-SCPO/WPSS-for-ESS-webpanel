# -- STDLIB
import time
from collections import Counter
from functools import wraps

# -- DJANGO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import BaseCommand, CommandError

# -- THIRDPARTY
from celery import group

# -- QXSMS
from hq.models import Panel
from manager import tasks
from manager.forms import CSVImportForm


def profile(fn):

    @wraps(fn)
    def inner(*args, **kwargs):
        fn_kwargs_str = ', '.join(f'{k}={v}' for k, v in kwargs.items())
        print(f'\n{fn.__name__}({fn_kwargs_str})')

        # Measure time
        t = time.perf_counter()
        retval = fn(*args, **kwargs)
        elapsed = time.perf_counter() - t
        print(f'Time   {elapsed:0.4}')

        return retval

    return inner


def pool_result(tasks, interval=0.5):  # do we need this ?
    while len(tasks):
        time.sleep(interval)
        for task in list(tasks):
            if task.ready():
                yield task.get()
                tasks.remove(task)


class Command(BaseCommand):
    help = 'Measure time to import CSV panelists'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--file', type=str, help='Path of the csv to upload')
        parser.add_argument('-p', '--panel', type=int, help='Panel id')
        parser.add_argument('-c', '--chunk', type=int, help='Chunk size')
        # By default, readonly fields are excluded since we most likely want to import back what we generate
        parser.add_argument('-r', '--include-readonly', action='store_true', help='Include readonly columns')

    @profile
    def time_import(self, panel_pk, dataset, chunk):
        list_tasks = []
        result = Counter()
        for i in range(0, len(dataset), chunk):
            raw_data = dataset[i:i + chunk]
            list_tasks.append(tasks.import_contact.s(panel_pk, raw_data, dataset.headers))
        group_tasks = group(list_tasks)
        results = group_tasks.apply_async()
        for r, b in pool_result(results):  # if we dont need to pool results : results.get()
            result.update(r)
            print(result)

    def handle(self, *args, **options):

        file = options['file']
        panel_pk = options['panel']

        try:
            panel = Panel.objects.get(pk=panel_pk)
            prompt = f"Import file {file} into panel {panel.name}? ([y]/n)"
            confirm = input(prompt)
            while confirm and confirm not in 'yYnN':
                confirm = input(prompt)
            if confirm not in 'yY':
                return
        except Panel.DoesNotExist:
            raise CommandError(f"No panel with id={panel_pk}.")

        with open(file, 'rb') as f:
            file = SimpleUploadedFile(f.name, f.read())

        form = CSVImportForm(files={'dataset': file})
        if not form.is_valid():
            raise CommandError(f"Invalid CSV file: {form.errors}")

        dataset = form.cleaned_data['dataset']

        chunk_size = options['chunk'] if options['chunk'] else len(dataset)

        self.time_import(panel_pk, dataset, chunk_size)

    def log_results(self, result):
        self.stdout.write(f"Results: {result.totals}")

    def log_errors(self, result):
        raise CommandError(f"Result errors: {result.errors}")
