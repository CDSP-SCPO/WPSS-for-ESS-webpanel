# -- STDLIB
import concurrent.futures
import time
from functools import wraps

# -- DJANGO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import BaseCommand, CommandError
from django.db import connection, connections, reset_queries

# -- THIRDPARTY
import tablib
from memory_profiler import memory_usage

# -- QXSMS
from hq.models import Panel
from manager.forms import CSVImportForm
from utils.csvimport import ProfileResource


def profile(fn):

    @wraps(fn)
    def inner(*args, **kwargs):
        fn_kwargs_str = ', '.join(f'{k}={v}' for k, v in kwargs.items())
        print(f'\n{fn.__name__}({fn_kwargs_str})')

        # Measure time & memory
        t = time.perf_counter()
        mem, query_count = memory_usage((fn, args, kwargs), retval=True, timeout=200, interval=1e-7)
        elapsed = time.perf_counter() - t
        print(f'Time   {elapsed:0.4}')
        print(f'Memory {max(mem) - min(mem)}')
        print(f'Queries {query_count}')

    return inner


def wrapper_queries(fn, *args, **kwargs):
    reset_queries()
    connections['default'].connect()  # reconnect to allow use of ProcessPoolExecutor
    r = fn(*args, **kwargs)
    return connection.queries, r


class Command(BaseCommand):
    help = 'Measure time to import CSV panelists'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--file', type=str, help='Path of the csv to upload')
        parser.add_argument('-p', '--panel', type=int, help='Panel id')
        parser.add_argument('-c', '--chunk', type=int, help='Chunk size')
        parser.add_argument('-t', '--threads', type=int, help='Number of threads', default=4)
        # By default, readonly fields are excluded since we most likely want to import back what we generate
        parser.add_argument('-r', '--include-readonly', action='store_true', help='Include readonly columns')

    @profile
    def time_import(self, resource, dataset, chunk, threads):
        total_query_count = 0
        # open threadpool
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            results = [executor.submit(wrapper_queries, resource.import_data,
                                       tablib.Dataset(*dataset[i:i + chunk], headers=dataset.headers), dry_run=True)
                       for i in range(0, len(dataset), chunk)]

            for f in results:
                queries, result = f.result()
                query_count = len(queries)
                total_query_count += query_count
                if result.has_errors():
                    self.log_errors(result)
                else:
                    self.log_results(result, query_count)
        return total_query_count

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

        resource = ProfileResource(panel_id=panel_pk)

        self.time_import(resource, dataset, chunk_size, options["threads"])

    def log_results(self, result, queries):
        self.stdout.write(f"Queries : {queries} Results : {result.totals}")

    def log_errors(self, result):
        raise CommandError(f"Result errors: {result.errors}")
