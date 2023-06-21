# -- DJANGO
from django.conf import settings
from django.core.mail import mail_admins
from django.core.management.base import BaseCommand, CommandError

# -- QXSMS
from qxauth.models import User


class Command(BaseCommand):
    help = "Creates an admin account and sends its credentials by email to ADMINS"

    def mail_admin_credentials(self, email, password):
        mail_admins(
            subject="Admin credentials",
            message=f"login: {email}\npassword: {password}",
        )

    def handle(self, *args, **options):
        try:
            for name, email in settings.ADMINS:
                if not User.objects.filter(email=email).exists():
                    password = User.objects.make_random_password()
                    User.objects.create_superuser(
                        email=email,
                        password=password,
                    )
                    self.mail_admin_credentials(email, password)
                    self.stdout.write(self.style.SUCCESS("Created admin and mailed credentials"))
                else:
                    self.stdout.write("Admin already exists, command ignored")
        except Exception:
            raise CommandError("Unknown error")
