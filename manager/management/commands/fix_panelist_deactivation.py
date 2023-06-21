# -- DJANGO
from django.core.management.base import BaseCommand
from django.db.models import Q

# -- QXSMS
from panelist.models import Profile


class Command(BaseCommand):
    help = "Runs deactivation process on manually anonymized profiles."
    filters = {
        "args": [Q(delete_contact_data=True) | Q(email__endswith="opinionsurvey.org")],
        "kwargs": {
            "anonymized_since": None,
        }
    }

    def add_arguments(self, parser):
        parser.add_argument("-d", "--dry", action="store_true", help="dry run mode")

    def handle(self, *args, **options):
        dry_run = options["dry"]
        profiles = Profile.objects.filter(*self.filters["args"], **self.filters["kwargs"])
        profiles_count = profiles.count()
        self.stdout.write(f"{dry_run=}\n{self.filters=}")
        self.stdout.write(f"{profiles_count} profiles found")
        if not profiles_count:
            return

        fields = ["country", "ess_id", "is_opt_out", "opt_out_date", "email"]
        self.stdout.write(",".join(fields))
        for profile in profiles:
            values = []
            for field in fields:
                value = str(getattr(profile, field))
                if field == "email":
                    # We only want to know if the domain is misspelled when manually set
                    value = value.split("@")[-1]
                values.append(value)
            self.stdout.write(",".join(values))
            if not dry_run:
                profile.deactivate()
