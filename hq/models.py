# -- STDLIB
import logging

# -- DJANGO
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)
User = get_user_model()


class Panel(models.Model):
    managers = models.ManyToManyField(User, blank=True)
    name = models.CharField(max_length=256)
    incentive_amount = models.CharField(max_length=256, blank=True, help_text=_("Value and currency."))
    contact_info = models.TextField(
        null=True,
        blank=True,
        help_text=_("Content that will be displayed in the \"Contact us\" section "
                    "at the end of the panelist portal help page. "
                    "If not set, the manager contact information will be displayed by default.")
    )

    def __str__(self):
        return self.name


class SMSStats(models.Model):
    panelist = models.ForeignKey("panelist.Profile", on_delete=models.CASCADE)
    msgdist = models.ForeignKey("distributions.MessageDistribution", on_delete=models.CASCADE)
    smsstatus = models.CharField(max_length=255, null=True)
    bouncereason = models.CharField(max_length=255, null=True)
    datefile = models.DateTimeField(null=True)

    def __repr__(self):
        return f"{self.panelist}|{self.msgdist}|{self.datefile}"
