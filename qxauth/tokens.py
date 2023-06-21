# -- DJANGO
from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailChangePanelistProfileTokenGenerator(PasswordResetTokenGenerator):

    def _make_hash_value(self, user, timestamp):
        email = user.profile.temp_email or user.email
        return str(user.pk) + user.password + email + str(timestamp)


class PhoneChangePanelistProfileTokenGenerator(PasswordResetTokenGenerator):

    def _make_hash_value(self, user, timestamp):
        return super()._make_hash_value(user, timestamp) + str(user.phone)


email_token_generator = EmailChangePanelistProfileTokenGenerator()
phone_token_generator = PhoneChangePanelistProfileTokenGenerator()
