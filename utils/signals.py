# -- DJANGO
from django.contrib import messages
from django.contrib.auth import user_logged_out
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    messages.add_message(
        request,
        messages.SUCCESS,
        _("{user} has been Logged out").format(user=str(user)),
    )
