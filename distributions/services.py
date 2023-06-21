# -- STDLIB
import functools
import logging
from collections import Counter, defaultdict
from datetime import datetime
from functools import wraps
from typing import Iterable

# -- DJANGO
from django.conf import settings
from django.core.cache import cache

# -- QXSMS
from distributions.models import (
    Link, get_link_status, get_msgdist_status, has_failed, has_finished,
    has_partially_finished, has_started,
)
from panelist.models import Profile

# -- QXSMS (LOCAL)
from . import client as xmc
from .client import format_datetime, parse_datetime

logger_name = __name__
if settings.DEBUG:
    logger_name = 'django.server'
# TODO Configure logger
logger = logging.getLogger(logger_name)


def cached(key_spec, timeout, backend=None):
    backend = backend or cache
    log_msg = "Cache %s for %s"

    def get_cached(func):
        @wraps(func)
        def wrapped(*, skip_cache=False, **kwargs):
            key = key_spec.format(**kwargs)
            if skip_cache:
                backend.delete(key)
            res = backend.get(key)
            outcome = 'hit'
            if res is None:
                outcome = 'skip' if skip_cache else 'miss'
                res = func(**kwargs)
                backend.set(key, res, timeout)
            logger.info(log_msg, outcome, key)
            return res

        return wrapped

    return get_cached


@cached(key_spec='surveys', timeout=300)
def get_surveys():
    # TODO Consider scheduling async DB update
    return xmc.list_surveys()


@cached(key_spec='messages', timeout=300)
def get_messages():
    # TODO Consider scheduling async DB update
    return xmc.list_messages()


QX_EMAIL_CATEGORIES = ('invite', 'reminder', 'thankYou', 'general')
QX_SUBJECT_CATEGORIES = ('emailSubject',)
QX_SMS_CATEGORIES = ('smsInvite',)


def _filter_categories(messages: Iterable[dict], categories: Iterable[str]) -> Iterable[dict]:
    return [msg for msg in messages if msg['category'] in categories]


filter_email_messages = functools.partial(_filter_categories, categories=QX_EMAIL_CATEGORIES)
filter_sms_messages = functools.partial(_filter_categories, categories=QX_SMS_CATEGORIES)
filter_email_subjects = functools.partial(_filter_categories, categories=QX_SUBJECT_CATEGORIES)


def _serialize_profiles(profiles):
    return [
        {
            'extRef': d["uid"].hex,
            'firstName': d['first_name'],
            'lastName': d['last_name'],
            'phone': str(d['phone']) if d['phone'] else '',
            'email': d['email'] or '',
            'embeddedData': {'panel': d['panel__name']}
        } for d in profiles
    ]


def _get_distribution_profiles(dist_id):
    attrs = ('uid', 'first_name', 'last_name', 'phone', 'email', 'panel__name')
    return list(Profile.objects.filter(panel__linkdistribution=dist_id).values(*attrs))


def get_distribution_contacts(dist_id):
    profiles = _get_distribution_profiles(dist_id)
    return _serialize_profiles(profiles)


@cached(key_spec='links-{qx_id}', timeout=300)
def list_distribution_links(*, qx_id, survey_id):
    return xmc.list_distribution_links(qx_id, survey_id)


@cached(key_spec='stats-{qx_id}', timeout=300)
def get_distribution_stats(*, qx_id: str, survey_id: str, is_sms: bool = False):
    dm = xmc.sms_distributions() if is_sms else xmc.distributions()
    return dm.stats(qx_id=qx_id, survey_id=survey_id)


# Distribution history
# --------------------


@cached(key_spec='history-{qx_id}', timeout=300)
def get_distribution_history(*, qx_id):
    dm = xmc.distributions()
    return dm.history(qx_id)


def get_contact_history(*, qx_id):
    """
    get contact history
    @params:
    history_type: default is email but we are looking here for response

    """
    dc = xmc.directory_contacts()
    response = dc.history(qx_id=qx_id, history_type='response')
    # the response of the api doesnt contains the contact
    # id https://qapi.qualtrics.com/api-reference/YXBpOjYwOTE3-contacts#get-contact-history

    return [dict(v, contactId=qx_id) for v in response]


def merge_links_and_history(links: list['Link'], history: list[dict]) -> list[dict]:  # noqa F821
    """Merge link attributes with progess information found in distribution's response history"""
    by_qx_id = {h.get('contactId'): h for h in history}
    res = []
    for link in links:
        qx_id = link.qx_contact_id
        merged = _merge_link_and_history_record(link, by_qx_id.get(qx_id, {}))
        res.append(merged)
    return res


def _merge_link_and_history_record(link: 'Link', record: dict) -> dict:  # noqa F821
    """Merge link attributes and response history record into a single dict

    Example of what we are interested in:
    {
      'status': 'SurveyFinished',
      'sentAt': '2021-05-01T08:03:22.430Z',
      'openedAt': '2021-05-01T10:10:13.000Z',
      'responseStartedAt': '2021-05-01T10:10:13.000Z',
      'responseCompletedAt': '2021-05-01T10:10:24.000Z',
    }

    Interpretation of different fields depends on whether we are dealing with a link distribution
    or a message.
    """
    return {
        'profile_id': link.profile.id,
        'ess_id': link.profile.ess_id,
        'panel': link.profile.panel.name,
        'panel_pk': link.profile.panel.pk,
        'phone': link.profile.phone,
        'email': link.profile.email,
        'full_name': link.profile.full_name,
        'url': link.url,
        'status': record.get('status'),
        'opened_at': parse_datetime(record.get('openedAt') or ''),
        'started_at': parse_datetime(record.get('responseStartedAt') or ''),
        'completed_at': parse_datetime(record.get('responseCompletedAt') or ''),
        'finished': has_finished(record),
        'started': has_started(record),
        'partially_finished': has_partially_finished(record),
        'failed': has_failed(record)
    }


def total_stats(result, history_links, stat_recp):
    """
    add total row if more than one panel
    add panel's primary key to stats
    """
    for k, v in result.items():
        elements_list = [e for e in v.elements() if e != 'opened']
        v['total'] = len(elements_list)

    total_all_panelists = 0
    for r in result:
        for link in history_links:
            if r == link['panel']:
                result[r]['pk'] = link['panel_pk']
                result[r]['total_panelists'] = Profile.objects.filter(panel=result[r]['pk']).count()
                total_all_panelists += result[r]['total_panelists']
                break

    # all stats
    if len(result) > 1:
        result['Total'] = stat_recp
        result['Total']['total'] = len(history_links)
        result['Total']['total_panelists'] = total_all_panelists
    return result


def history_links_stats(history_links: list) -> dict:
    """
    Status frequencies grouped by panel

    ex:
    {
        'panel 1': {'Started': 2, 'SurveyFinished': 2},
        'panel 2': {'Pending': 1, 'SurveyFinished': 2}
    }
    """
    # stats by panel
    by_panel = defaultdict(list)
    # total stats
    stat_recp = dict(not_started=0, started=0,
                     finished=0, partially_finished=0, failed=0)

    for h in history_links:
        p = h.get('panel', 'Unknown panel')
        status = get_link_status(h)
        stat_recp[status] += 1

        by_panel[p].append(status)

    result = {p: Counter(g) for p, g in by_panel.items()}
    return total_stats(result, history_links, stat_recp)


def msg_distributions_stats(history_links: list) -> dict:
    # stats by panel
    by_panel = defaultdict(list)
    # total stats
    stat_recp = dict(sent=0, success=0, opened=0,
                     soft_bounced=0, hard_bounced=0,
                     failed=0)

    for h in history_links:
        p = h.get('panel', 'Unknown panel')
        status = get_msgdist_status(h)
        if status == 'opened':
            stat_recp['success'] += 1
            by_panel[p].append('success')
        stat_recp[status] += 1

        by_panel[p].append(status)

    result = {p: Counter(g) for p, g in by_panel.items()}
    return total_stats(result, history_links, stat_recp)


# Email distributions
# -------------------


def send_email_distribution(*, contacts: list[dict], list_id: str, message_id: str, subject_id: str) -> str:
    """Send an email to given contacts

    This service is currently not used, but serves as a clear illustration of the sequential
    email distribution workflow.

    1. Create an empty transaction batch
    2. Import `contacts` with latest email, and individual survey links as transaction data into `mlist`
    3. Create an email distribution for the batch

    - `contacts`: [{'id': '1', email: 'foo@bar.com', 'survey_link': '<link>'}]

    """
    tbm = xmc.transaction_batches()
    batch_id = tbm.create()
    cim = xmc.contact_imports(list_id)
    qx_import_id = cim.start_contact_import(contacts=contacts, batch_id=batch_id)
    cim.wait_until_complete(qx_import_id)
    dm = xmc.distributions()
    qx_id = dm.send(
        batch_id=batch_id,
        survey_id=settings.QXSMS_SEND_SURVEY,
        message_id=message_id,
        subject_id=subject_id,
    )
    return qx_id


def send_single_sms_distribution(*, name: str, contact: dict, message: str) -> str:
    """Send a single sms to a contact.

    A mailinglist_id or transactionbatch_id is required when the type of invite is "Invite.
    A contact_id ("contactLookupId") can be specified but since the mailinglist only has 1 contact,
    it is not necessary.

    If the message is the same than a previously sent one, qualtrics does not send it.
    It should work like email duplicates.
    However, we cannot query the API to know if a SMS distribution has been marked as duplicate.
    We can however check if the recipient lis is not empty (might be a lagging stat though).
    """

    # Create mailinglist
    mlm = xmc.mailing_lists()
    ml_name = f"SINGLESMS_{contact.get('extRef')}_{format_datetime(datetime.now())}"  # name: SINGLESMS_<extRef>_<date>
    ml_id = mlm.create(ml_name)

    # Create contact in mailinglist
    mlcm = xmc.mailing_list_contacts(ml_id)
    mlcm.create(contact)

    # Send sms
    dm = xmc.sms_distributions()
    qx_id = dm.send_single(
        name=name,
        survey_id=settings.QXSMS_SEND_SURVEY,
        message=message,
        mailinglist_id=ml_id,
    )
    return qx_id
