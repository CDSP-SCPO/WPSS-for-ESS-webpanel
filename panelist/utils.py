# -- STDLIB
import hashlib
from typing import List

# -- DJANGO
from django.utils.translation import gettext_lazy as _

# -- QXSMS
from distributions.client import parse_datetime
from distributions.models import Link


def obfuscate(length):

    def do_hash(s):
        if '@' not in s:
            return _hash(s)[:length]

        user, domain = s.split('@')
        domain, extension = domain.split('.')
        return f'{_hash(user)[:length]}@{_hash(domain)[:length]}.eu'

    return do_hash


def _hash(s):
    b = s.encode('utf8')
    return hashlib.md5(b).hexdigest()


def panelist_merge_links_and_history(links: List[Link], history: List[dict]) -> List[dict]:
    """Merge link attributes with progess information found in distribution's response history"""
    by_qx_id = {h.get('distributionId'): h for h in history}
    res = []
    for link in links:
        qx_id = link.distribution.qx_id
        merged = _panelist_merge_link_and_history_record(link, by_qx_id.get(qx_id, {}))
        res.append(merged)
    return res


def _panelist_merge_link_and_history_record(link: Link, record: dict) -> dict:
    """Merge link attributes and response history record into a single dict

    Example of what we are interested in:
    {
        "distributionId": "EMD_eanPyQa5ondBhkN",
        "responseId": "R_rfjAlFwK65ZsNYR",
        "surveyCompletedDate": "2017-08-17 22:32:27",
        "surveyFinished": true,
        "surveyId": "SV_6hZDPZroTErKGZD",
        "surveyStartedDate": "2017-08-17 22:32:16"
    }

    Interpretation of different fields depends on whether we are dealing with a link distribution
    or a message.
    """
    link = {
        'url': link.url,
        'opened_at': parse_datetime(record.get('openedAt') or ''),
        'started_at': parse_datetime(record.get('responseStartedAt') or ''),
        'completed_at': parse_datetime(record.get('responseCompletedAt') or ''),
        'is_survey_finished': record.get('surveyFinished'),
        'survey_started_date': record.get('surveyStartedDate'),
        'survey_completed_date': record.get('surveyCompletedDate'),
        'distribution_id': link.distribution.short_uid,
        'survey_name': link.distribution.survey.name,
        'is_distribution_expired': link.distribution.is_expired,
        'distribution_expiration_date': link.distribution.expiration_date,
    }

    if link['is_survey_finished']:
        link['status_css'] = 'success'
        link['status'] = _('Completed')
    else:
        if link['survey_started_date']:
            link['status_css'] = 'info'
            link['status'] = _('Started')

        else:
            link['status_css'] = 'secondary'
            link['status'] = _('Not Started')

    return link
