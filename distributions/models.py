# -- STDLIB
import logging
import uuid
from typing import Iterable, List, Set, Tuple

# -- DJANGO
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# -- QXSMS
from panelist.models import Profile


class Survey(models.Model):
    qx_id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Distribution(models.Model):

    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=200)
    qx_id = models.CharField(max_length=20, unique=True, null=True)
    qx_import_id = models.CharField(max_length=20, unique=True, null=True)
    qx_created_date = models.DateTimeField(null=True)

    class Meta:
        abstract = True
        ordering = ['-created_date']

    @property
    def short_uid(self):
        if self.uid is None:
            return ''
        return self.uid.hex[:8]

    def __str__(self):
        descr = self.description or ''
        return f"({self.short_uid}) {descr}"

    def candidates(self, *args, **kwargs):
        raise NotImplementedError

    def contacts_for_import(self):
        raise NotImplementedError

    def save_links(self):
        raise NotImplementedError

    def get_import_kwargs(self):
        """Keyword arguments as expected by `client.import_contacts()`"""
        return {'list_id': self.qx_list_id, 'contacts': self.contacts_for_import()}


def _update_links(links: Iterable['Link'], qx_links: List[dict]) -> Tuple[List['Link'], List['Link']]:
    """Set `Link` attributes using links fetched from Qualtrics

    The normal behavior is that each `Link` instance has exactly one counterpart in `qx_list`.
    If no corresponding Qualtrics link is found, log the error.
    Return updated and skipped instances separately to the caller.
    """
    by_ext_ref = {qxl['externalDataReference']: qxl for qxl in qx_links}
    updated = []
    skipped = []
    for link in links:
        ext_ref = link.profile_id.hex
        try:
            qx_link = by_ext_ref[ext_ref]
        except KeyError:
            logging.error("missing Qualtrics link for %s", link.profile_id)
            skipped.append(link)
            continue
        link.qx_contact_id = qx_link.get('contactId')
        link.url = qx_link.get('link')
        if not (link.qx_contact_id and link.url):
            logging.error("missing contactId or link in record: %s", qx_link)
            skipped.append(link)
            continue
        updated.append(link)
    return updated, skipped


class LinkDistribution(Distribution):

    qx_list_id = models.CharField(max_length=20, unique=True, null=True)
    expiration_date = models.DateTimeField(blank=False, null=True)
    survey = models.ForeignKey('Survey', to_field='qx_id', related_name="distributions",
                               limit_choices_to={'is_active': True}, on_delete=models.PROTECT)
    panels = models.ManyToManyField('hq.Panel', related_name="distributions")

    def get_absolute_url(self):
        return reverse('dist:detail', args=[self.pk])

    def candidates(self):
        return Profile.objects.filter(panel__in=self.panels.all(), is_opt_out=False)

    @property
    def count_candidates(self):
        return self.candidates().count()

    def contacts_for_import(self):
        """Serialize contacts that need a link, in the format expected by Qualtrics imports

        Intended to be called *after* `save_links()`. Another choice would have been to call
        `candidates()` to get the target queryset, but this would leave the possibility of the set
        of candidates having changed since we called `save_links()`...
        """
        profiles = Profile.objects.prefetch_related('blankslotvalue_set__blankslot').filter(link__distribution=self)
        return [p.to_json() for p in profiles]

    def save_links(self):
        """Create links with empty URLs to record the profiles for which link generation is intended

        By creating `Link` instances *before* creating the distribution on Qualtrics, we can confirm that
        all intended recipients indeed got a link generated.
        """
        profiles = self.candidates()
        links = [Link(profile=profile, distribution=self) for profile in profiles]
        self.links.all().delete()
        return Link.objects.bulk_create(links)

    def update_links(self, qx_links: List[dict]) -> Tuple[List['Link'], List['Link']]:
        """Update database links with data from their corresponding Qualtrics link

        `Link` instances for each recipient saved in the database before the Qualtrics distribution is created.
        Once the links are generated on Qualtrics and retrieved, we need to set `Link.qx_contact_id` and
        `Link.url` on their counterparts.

        The pairing between a Qualtrics link and a database `Link` is done using `externalDataReference`, which
        matches `Link.profile_id`.
        """
        updated, skipped = _update_links(self.links.all(), qx_links)
        Link.objects.bulk_update(updated, fields=['qx_contact_id', 'url'])
        return updated, skipped

    @property
    def is_expired(self):
        return timezone.now() > self.expiration_date


class Link(models.Model):
    # TODO Parse and cache URL components for use in __str__
    URL_PATTERN = r'^.*(?P<survey_qx_id>SV_.*)\?Q_CHL=gl&Q_DL=(?P<qx_id>.*)$'

    profile = models.ForeignKey('panelist.Profile', to_field='uid', related_name='links', related_query_name='link',
                                on_delete=models.CASCADE)
    distribution = models.ForeignKey('LinkDistribution', on_delete=models.CASCADE,
                                     related_name='links', related_query_name='link')
    url = models.URLField()
    qx_contact_id = models.CharField(max_length=20)

    class Meta:
        unique_together = ('profile', 'distribution')

    def __str__(self):
        dist_id = profile_id = ""
        if self.distribution_id is not None:
            dist_id = str(self.distribution_id)[:8]
        if self.profile_id is not None:
            profile_id = str(self.profile_id)[:8]
        return (f"dist={dist_id}, "
                f"profile={profile_id}")


# Message distributions (Email and SMS)
# -------------------------------------

class MessageDistribution(Distribution):

    MODE_EMAIL = 0
    MODE_SMS = 1
    CONTACT_MODE_CHOICES = (
        (MODE_EMAIL, _("Email")),
        (MODE_SMS, _("SMS")),
    )

    TARGET_ALL = 0
    TARGET_NOT_FINISHED = 1
    TARGET_FINISHED = 2
    TARGET_CHOICES = (
        (TARGET_ALL, _("All")),
        (TARGET_NOT_FINISHED, _("Not finished (proper target for reminders)")),
        (TARGET_FINISHED, _("Finished"))
    )

    link_distribution = models.ForeignKey('LinkDistribution', on_delete=models.CASCADE,
                                          related_name="%(class)ss", related_query_name="%(class)s",
                                          # TODO Really necessary restriction ?
                                          limit_choices_to={'qx_id__isnull': False})
    qx_batch_id = models.CharField(max_length=20, unique=True, null=True)
    contact_mode = models.PositiveSmallIntegerField(choices=CONTACT_MODE_CHOICES)
    target = models.PositiveSmallIntegerField(choices=TARGET_CHOICES, verbose_name=_("Target recipients"))
    send_date = models.DateTimeField(blank=False, null=True)
    links = models.ManyToManyField('Link', related_name="message_distributions",
                                   related_query_name='message_distribution')
    message = models.ForeignKey('Message', related_name="email_message_of_set",
                                related_query_name='email_message_of', on_delete=models.SET_NULL, null=True)
    subject = models.ForeignKey('Message', related_name="email_subject_of_set",
                                related_query_name='email_subject_of', on_delete=models.SET_NULL, null=True)
    fallback_of = models.OneToOneField('self', related_name='fallback', null=True, on_delete=models.CASCADE)

    @property
    def qx_list_id(self):
        list_id = None
        if self.link_distribution_id is not None:
            list_id = self.link_distribution.qx_list_id
        return list_id

    @property
    def is_email(self):
        return self.contact_mode == MessageDistribution.MODE_EMAIL

    @property
    def is_sms(self):
        return self.contact_mode == MessageDistribution.MODE_SMS

    @property
    def fallback_contact_mode(self):
        return MessageDistribution.MODE_EMAIL if self.is_sms else MessageDistribution.MODE_SMS

    @property
    def contact_label(self):
        return "Sms" if self.is_sms else "Email"

    @property
    def fallback_label(self):
        return "Sms" if self.is_email else "Email"

    @property
    def is_fallback(self):
        return self.fallback_of is not None

    @property
    def has_fallback(self):
        return hasattr(self, 'fallback')

    @property
    def can_add_fallback(self):
        return not (self.is_fallback or self.has_fallback)

    @property
    def has_history(self):
        """Whether a detailed history of response statuses is available

        Qualtrics does not seem to support response history for SMS distributions.
        """
        return self.qx_id and self.is_email

    def get_send_date(self):
        if self.fallback_of is not None:
            return self.fallback_of.send_date
        return self.send_date

    def get_absolute_url(self):
        return reverse('dist:msgd:detail', args=[self.pk])

    def contacts_for_import(self):
        return [_contact_from_link(link) for link in self.links.select_related('profile__panel')]

    def candidates(self, history: Iterable[dict] = (), select_related: Iterable[str] = ()) -> List[Link]:
        """Using our link distribution's response history, select eligible candidates for this message.

        The initial set of candidates consists of all the profiles that are part of our link distribution.

        - First, only keep those that can be reached through our
        contact mode (and only thus if we are used as a fallback).

        - Second, using the response history, only keep those that
        correspond to our target (all, survey not started, or survey
        finished)

        """
        select_related = [f"profile__{field}" for field in select_related] + ['profile']
        links = self.link_distribution.links.select_related(*select_related)
        links = links_for_completion_status(links, target=self.target, history=history)
        only = self.fallback_of is not None
        return links_for_contact_mode(links, contact_mode=self.contact_mode, only=only)

    def get_candidates_stats(self, history):
        links = self.link_distribution.links.all()
        links = links_for_completion_status(links, target=self.target, history=history)

        contact_count = len(links_for_contact_mode(links, contact_mode=self.contact_mode))
        fallback_count = len(links_for_contact_mode(links, contact_mode=self.fallback_contact_mode, only=True))
        total = contact_count + fallback_count
        stats = {
            'contact_mode': contact_count,
            'fallback_mode': fallback_count,
            'total': total,
            'unreachable': len(links) - total,
        }

        return stats

    def save_links(self, history):
        """Freeze the set of candidates, recording them as the recipients of the distribution."""
        self.links.set(self.candidates(history=history))

    def get_import_kwargs(self):
        kwargs = super().get_import_kwargs()
        kwargs['batch_id'] = self.qx_batch_id
        return kwargs

    def add_fallback(self, *, message, subject=None):
        kwargs = {
            'contact_mode': self.fallback_contact_mode,
            'target': self.target,
            'link_distribution': self.link_distribution,
            'description': self.description,
            'message': message,
            'subject': subject,
        }
        fallback = MessageDistribution.objects.create(**kwargs)
        fallback.fallback_of = self
        fallback.save()


def links_for_contact_mode(links: Iterable[Link],
                           *, contact_mode: int, only: bool = False) -> List[Link]:
    """Filter profiles that can receive a message using given contact mode.

    If `only == True`, require that it be the only possible contact mode.
    """
    if contact_mode == MessageDistribution.MODE_EMAIL:
        filter_func = _can_rcv_email
    else:
        filter_func = _can_rcv_sms
    return [link for link in links if filter_func(link.profile, only=only)]


def links_for_completion_status(links: Iterable[Link], target: int, history: Iterable[dict]) -> List[Link]:
    """Filter links based on their survey completion status"""
    qx_ids = _filter_completion_status(history, target)
    return [link for link in links if link.qx_contact_id in qx_ids]


# TODO Make `Profile.can_rcv_email()`
def _can_rcv_email(profile: Profile, only: bool = False) -> bool:
    res = profile.email and not profile.no_email
    if only:
        res = res and not _can_rcv_sms(profile)
    return res and not profile.is_opt_out


# TODO Make `Profile.can_rcv_sms()`
def _can_rcv_sms(profile: Profile, only: bool = False) -> bool:
    res = profile.phone and not profile.no_text
    if only:
        res = res and not _can_rcv_email(profile)
    return res and not profile.is_opt_out


def _contact_from_link(link: Link) -> dict:
    contact = link.profile.to_json()
    contact['transactionData'] = {'survey_link': link.url}
    return contact


HISTORY_STATUS_PENDING = {"Pending"}
HISTORY_STATUS_STARTED = {"SurveyStarted"}
HISTORY_STATUS_OPENED = {"Opened"}
HISTORY_STATUS_SUCCESS = {"Success"}
HISTORY_STATUS_SOFT_BOUNCED = {"SoftBounce"}
HISTORY_STATUS_HARD_BOUNCED = {"HardBounce"}
HISTORY_STATUS_FINISHED = {"SurveyFinished"}
HISTORY_STATUS_PARTIALLY_FINISHED = {"SurveyPartiallyFinished"}

HISTORY_STATUS_NOT_FAILED = {*HISTORY_STATUS_SUCCESS, *HISTORY_STATUS_FINISHED, *HISTORY_STATUS_STARTED,
                             *HISTORY_STATUS_PENDING, *HISTORY_STATUS_OPENED,
                             *HISTORY_STATUS_HARD_BOUNCED, *HISTORY_STATUS_SOFT_BOUNCED}


def has_finished(record: dict) -> bool:
    """Survey has been completed"""
    return record.get('status') in HISTORY_STATUS_FINISHED


def has_partially_finished(record: dict) -> bool:
    """Survey has been partially completed and the time limit is passed"""
    return record.get('status') in HISTORY_STATUS_PARTIALLY_FINISHED


def has_started(record: dict) -> bool:
    """Survey has been started, but not completed"""
    return record.get('status') in HISTORY_STATUS_STARTED


def is_soft_bounced(record: dict) -> bool:
    return record.get('status') in HISTORY_STATUS_SOFT_BOUNCED


def is_hard_bounced(record: dict) -> bool:
    return record.get('status') in HISTORY_STATUS_HARD_BOUNCED


def is_success(record: dict) -> bool:
    return record.get('status') in HISTORY_STATUS_SUCCESS


def has_opened(record: dict) -> bool:
    """Survey has been sent and opened"""
    return record.get('status') in HISTORY_STATUS_OPENED


def has_failed(record: dict) -> bool:
    """Survey has been sent, but failed"""
    return record.get('status') not in HISTORY_STATUS_NOT_FAILED


def get_msgdist_status(record: dict) -> str:

    status = 'sent'
    if is_success(record):
        status = 'success'

    elif has_opened(record):
        status = 'opened'

    elif is_soft_bounced(record):
        status = 'soft_bounced'

    elif is_hard_bounced(record):
        status = 'hard_bounced'

    elif has_failed(record):
        status = 'failed'

    return status


def get_link_status(record: dict) -> str:
    status = 'not_started'
    if has_started(record):
        status = 'started'

    elif has_finished(record):
        status = 'finished'

    elif has_partially_finished(record):
        status = 'partially_finished'

    elif has_failed(record):
        status = 'failed'

    return status


def _filter_completion_status(history: Iterable[dict], target: int) -> Set[str]:
    if target == MessageDistribution.TARGET_FINISHED:
        history = [r for r in history if has_finished(r)]
    elif target == MessageDistribution.TARGET_NOT_FINISHED:
        history = [r for r in history if not has_finished(r)]
    return set(record.get('contactId') for record in history)


class Message(models.Model):
    EMAIL_INVITE = 'invite'
    REMINDER = 'reminder'
    EMAIL_SUBJECT = 'emailSubject'
    SMS_INVITE = 'smsInvite'
    CATEGORIES = (
        (EMAIL_INVITE, _("Email")),
        (EMAIL_SUBJECT, _("Email subject")),
        (SMS_INVITE, _("SMS"))
    )
    qx_id = models.CharField(max_length=20, primary_key=True)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    description = models.CharField(max_length=256)
