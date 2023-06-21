# -- STDLIB
import itertools
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

# -- DJANGO
from django.conf import settings

# -- THIRDPARTY
import requests

logger = logging.getLogger(__name__)


# Exceptions
# ----------
# TODO Make inherit from requests.exceptions.HTTPError
class QxError(Exception):
    """HTTP error returned by the Qualtrics API"""

    def __init__(self, *, status_code, reason, error_message, error_code, request_id):
        self.status_code = status_code
        self.reason = reason
        self.error_message = error_message
        self.error_code = error_code
        self.request_id = request_id

    @classmethod
    def from_json(cls, status_code, reason, response_meta):
        """Construct an error class from the JSON body of a Qualtrics error response

        Example:
            {
              "meta": {
                "httpStatus": "404 - Not Found",
                "error": {
                  "errorMessage": "API call does not exist: GET /API/v3/doesnotexist"
                }
              }
            }
        """
        request_id = response_meta.get('requestId', '')
        try:
            error_dict = response_meta['error']
        except KeyError:
            error_message = error_code = ''
        else:
            error_message = error_dict.get('errorMessage', '')
            error_code = error_dict.get('errorCode', '')
        return cls(
            status_code=status_code,
            reason=reason,
            error_message=error_message,
            error_code=error_code,
            request_id=request_id,
        )

    def __str__(self):
        return (
            f"{self.__class__.__name__}: "
            f"({self.status_code} - {self.reason} - {self.error_code}) "
            f"{self.error_message}"
        )


class QxClientError(QxError):
    """Client HTTP error"""
    pass


class QxServerError(QxError):
    """Server-originating HTTP error"""
    pass


class QxPollTimeout(Exception):
    pass


def raise_qx_error(status_code, reason, response_meta):
    # TODO Implement as a context manager
    if status_code >= 500:
        cls = QxServerError
    else:
        cls = QxClientError
    raise cls.from_json(status_code, reason, response_meta) from None


# Utilities
# ---------
RESULT_KEY = 'result'
RESULT_LIST_KEY = 'elements'
NEXT_PAGE_KEY = 'nextPage'
META_KEY = 'meta'
ID_KEY = 'id'
DATETIME_FORMAT_ISO = "%Y-%m-%dT%H:%M:%SZ"
DATETIME_FORMAT_ISO_MICROSEC = "%Y-%m-%dT%H:%M:%S.%fZ"
DATETIME_FORMAT_SIMPLE = "%Y-%m-%d %H:%M:%S"
MAX_PAGE_SIZE = 100

# Defaults
# -----------

DEFAULT_FROM_NAME = getattr(settings, 'DISTRIBUTIONS_EMAIL_FROM_NAME', "Qualtrics")
DEFAULT_FROM_EMAIL = getattr(settings, 'DISTRIBUTIONS_EMAIL_FROM', "noreply@qemailserver.com")
DEFAULT_REPLY_TO = getattr(settings, 'DISTRIBUTIONS_EMAIL_REPLY', "noreply@qualtrics.com")
DEFAULT_LINK_TYPE = "Anonymous"
DEFAULT_LINK_EXPIRATION_DAYS = 30


def _urljoin(*parts):
    cleaned_parts = []
    for part in parts:
        part = part.strip('/')
        # Absolute URL
        if "http" in part:
            cleaned_parts = []
        cleaned_parts.append(part)
    return "/".join(cleaned_parts)


def _pluck_result(response_dict):
    return response_dict.get(RESULT_KEY, {})


def _pluck_result_list(response_dict):
    result = response_dict.get(RESULT_KEY)
    return result.get(RESULT_LIST_KEY, [])


def _pluck_meta(response_dict):
    return response_dict.get(META_KEY, {})


def _pluck_result_id(response: dict) -> str:
    # TODO Still necessary to special-case distributions ?
    """Get the result ID from a Qualtrics response

    >>> response = {'result': {'id': 'QX_AbCd'}}
    >>> _get_response_result_id(response)
    'QX_AbCd'

    :param response (dict): Parsed Qualtrics JSON response
    :returns (str): ID of the (usually created) object
    """
    result = _pluck_result(response)
    return result.get(ID_KEY, '')


def parse_datetime(ts: str) -> Optional[datetime]:
    """Parse Qualtrics timestamp response to a datetime object
    """
    for fmt in (DATETIME_FORMAT_SIMPLE, DATETIME_FORMAT_ISO_MICROSEC, DATETIME_FORMAT_ISO):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            pass
    logger.debug("Unable to parse timestamp: %s", ts)
    return None


def format_datetime(dt: Optional[datetime] = None, iso: bool = True):
    """Format datetime as expected by Qualtrics"""
    fmt = DATETIME_FORMAT_ISO if iso else DATETIME_FORMAT_SIMPLE
    dt = dt or datetime.now()
    return dt.strftime(fmt)


def _iter_pages(client, url, *, num_pages=None, query_data=None):
    rng = itertools.count() if num_pages is None else range(num_pages)
    # Query parameters are included in the next page URL
    query_data = query_data or {}
    qs = '&'.join(f"{k}={v}" for k, v in query_data.items())
    next_page = f"{url}?{qs}"
    logger.info(f"Listing entities at {url}")
    for i in rng:
        if next_page is None:
            break
        logger.info(f'Fetching page {i + 1}')
        r = client.get(next_page)
        yield from r.get(RESULT_LIST_KEY, [])
        next_page = r.get(NEXT_PAGE_KEY, None)
        logger.info(f'Next: {next_page}')


# Client class
class XMDirectory:
    """Connection to Qualtrics

    Build API endpoint base URL
    Setup authentication headers (using Qualtrics API tokens).
    Set default directory and library IDs to be used.
    """

    def __init__(self, *, api_key, domain, directory_id=None, library_id=None, session=None):
        # TODO Make directory ID and library ID optional
        self.api_key = api_key
        self.domain = domain
        self.base_url = f"https://{domain}.qualtrics.com/API/v3/"
        self.session = session or requests.Session()
        self.session.headers.update({'X-API-TOKEN': api_key})
        # Bind the client to a default directory and library
        self.directory_id = directory_id
        self.library_id = library_id

    def http_request(self, method, path, query_data=None, json_data=None):
        """Send an HTTP request to Qualtrics and return the parsed response body"""
        url = _urljoin(self.base_url, path)
        resp = self.session.request(
            method,
            url,
            params=query_data or None,
            json=json_data or None,
        )

        try:
            response_dict = resp.json()
        except ValueError:
            response_dict = {}

        try:
            resp.raise_for_status()
        except requests.HTTPError:
            response_meta = _pluck_meta(response_dict)
            raise_qx_error(resp.status_code, resp.reason, response_meta)

        return response_dict

    def list(self, path, *, num_pages=None, query_data=None):
        """Return a list of entities from Qualtrics"""

        gen = _iter_pages(self, path, num_pages=num_pages, query_data=query_data)
        return list(gen)

    def get(self, path, query_data=None):
        """Return a single entity from Qualtrics"""

        response_dict = self.http_request('GET', path, query_data=query_data)
        return _pluck_result(response_dict)

    def post(self, path, json_data=None):
        """Create entity on Qualtrics and return its ID"""

        response_dict = self.http_request('POST', path, json_data=json_data)
        return _pluck_result_id(response_dict)

    def delete(self, path):
        """Delete an entity from Qualtrics"""

        self.http_request('DELETE', path)

    def put(self, path, json_data):
        """Patch an entity on Qualtrics"""

        self.http_request('PUT', path, json_data=json_data)

    @property
    def surveys(self):
        return SurveyManager(client=self)

    @property
    def distributions(self):
        return DistributionManager(client=self)

    @property
    def mailing_lists(self):
        return MailingListManager(client=self, directory_id=self.directory_id)

    @property
    def messages(self):
        return MessageManager(client=self, library_id=self.library_id)

    @property
    def sms_distributions(self):
        return SMSDistributionManager(client=self)

    @property
    def transaction_batches(self):
        return TransactionBatchManager(client=self, directory_id=self.directory_id)

    @property
    def directory_contacts(self):
        return DirectoryContactManager(client=self, directory_id=self.directory_id)

    @property
    def transactions(self):
        return TransactionManager(client=self, directory_id=self.directory_id)

    def mailing_list_contacts(self, list_id):
        return MailingListContactManager(client=self, directory_id=self.directory_id, list_id=list_id)

    def contact_imports(self, list_id):
        return ContactImportManager(client=self, directory_id=self.directory_id, list_id=list_id)


class BaseManager:
    path_spec = ''

    def __init__(self, *, client, **kwargs):
        # TODO kwargs validation based on path_spec
        self.client = client
        self.path = self.path_spec.format(**kwargs)

    def list(self, *, num_pages=None, query_data=None):
        return self.client.list(self.path, num_pages=num_pages, query_data=query_data)

    def get(self, qx_id, query_data=None):
        path = _urljoin(self.path, qx_id)
        return self.client.get(path, query_data=query_data)

    def create(self, json_data):
        return self.client.post(self.path, json_data=json_data)

    def update(self, qx_id, json_data):
        path = _urljoin(self.path, qx_id)
        return self.client.put(path, json_data)

    def delete(self, qx_id):
        path = _urljoin(self.path, qx_id)
        return self.client.delete(path)


# Mailing lists
# -------------

class MailingListManager(BaseManager):
    path_spec = 'directories/{directory_id}/mailinglists'

    def create(self, name):
        # TODO Owner of the mailing list ?
        return super().create(json_data={'name': name})


class MailingListContactManager(BaseManager):
    path_spec = 'directories/{directory_id}/mailinglists/{list_id}/contacts'

    def list(self, *, page_size=MAX_PAGE_SIZE, num_pages=None):
        query_data = {
            'useNewPaginationScheme': 'true',
            'pageSize': page_size
        }
        return super().list(num_pages=num_pages, query_data=query_data)

# Contact imports
# ---------------


def _is_complete(stats):
    return stats.get('status') == 'complete'


def _progress(stats):
    return int(stats.get('percentComplete', 0))


def _poll(target, step, check_success=lambda x: bool(x), max_tries=None):
    tries = 0
    if max_tries is not None:
        assert max_tries > 0, "Should at least try once!"
    while True:
        val = target()
        logger.info(f"Try {tries + 1}: {val}")
        if check_success(val):
            return val
        tries += 1
        # Sleep only if we have not exceeded max_tries
        if max_tries is not None and tries >= max_tries:
            raise TimeoutError("Giving up polling.")
        logger.info(f"(Next in {step}s)")
        time.sleep(step)
        step = step * 2


def _inspect_transaction_fields(contacts):
    data = (c['transactionData'] for c in contacts)
    unique_keys = set(itertools.chain(*data))
    return list(unique_keys)


class ContactImportManager(BaseManager):
    path_spec = 'directories/{directory_id}/mailinglists/{list_id}/transactioncontacts'

    list = None

    def stats(self, qx_id):
        url = _urljoin(self.path, qx_id)
        return self.client.get(url)

    def progress(self, qx_id):
        s = self.stats(qx_id)
        return _progress(s)

    def start_import(self, contacts, batch_id=None, transaction_fields=None):
        if not contacts:
            raise_qx_error(400, "Empty contact list not Allowed", {})

        json_data = {
            "contacts": contacts
        }
        if batch_id:
            if transaction_fields is None:
                transaction_fields = _inspect_transaction_fields(contacts)
            json_data['transactionMeta'] = {
                "batchId": batch_id,
                "fields": transaction_fields
            }
        return self.create(json_data=json_data)

    def wait_until_complete(self, qx_id, step=1, max_tries=None):
        return _poll(target=lambda: self.stats(qx_id), check_success=_is_complete, step=step, max_tries=max_tries)


# Distributions
# -------------

def _email_distribution_spec(*, from_email, from_name, reply_to, subject_id, library_id, message_id,
                             batch_id, survey_id, link_type,
                             link_expiration_date: datetime,
                             send_date: datetime):
    """Format JSON object to create an Email distribution targeting a transaction batch"""
    if link_type not in DistributionManager.LINK_TYPES:
        err_msg = ("Invalid link type: '%s'. "
                   "Possible choices are %s")
        raise ValueError(err_msg, link_type, ', '.join(DistributionManager.LINK_TYPES))
    return {
        "header": {
            "fromEmail": from_email,
            "fromName": from_name,
            "replyToEmail": reply_to,
            "subject": subject_id
        },
        "message": {
            "libraryId": library_id,
            "messageId": message_id
        },
        "recipients": {
            "transactionBatchId": batch_id
        },
        'surveyLink': {
            "surveyId": survey_id,
            "expirationDate": format_datetime(link_expiration_date),
            "type": link_type
        },
        "sendDate": format_datetime(send_date)
    }


class DistributionManager(BaseManager):
    path_spec = 'distributions'

    LINK_INDIVIDUAL = 'Individual'
    LINK_ANONYMOUS = 'Anonymous'
    LINK_MULTIPLE = 'Multiple'
    LINK_TYPES = (LINK_INDIVIDUAL, LINK_ANONYMOUS, LINK_MULTIPLE)
    CREATE_DISTRIBUTION_ACTION = 'CreateDistribution'

    def get(self, qx_id, *, survey_id):
        query_data = {"surveyId": survey_id}
        return super().get(qx_id, query_data=query_data)

    def stats(self, qx_id, survey_id):
        """Global distribution stats

        Example:
            {
              'sent': 0,
              'failed': 0,
              'started': 1,
              'bounced': 0,
              'opened': 1,
              'skipped': 0,
              'finished': 1,
              'complaints': 0,
              'blocked': 0
            }
        """
        data = self.get(qx_id, survey_id=survey_id)
        return data.get('stats')

    def generate_links(self, *, survey_id, expiration_date, description, list_id=None, batch_id=None):
        if bool(list_id) == bool(batch_id):
            raise ValueError("Specify either a mailing list, or a transaction batch ID")
        if list_id:
            target = {'mailingListId': list_id}
        else:
            target = {'transactionBatchId': batch_id}
        spec = {
            "surveyId": survey_id,
            "linkType": DistributionManager.LINK_INDIVIDUAL,
            "description": description,
            "action": DistributionManager.CREATE_DISTRIBUTION_ACTION,
            "expirationDate": format_datetime(expiration_date, iso=False),
            "mailingListId": list_id,
            **target
        }
        return self.client.post(self.path, json_data=spec)

    def send(self, *,
             # Recipients
             batch_id: str, survey_id: str, send_date: Optional[datetime] = None,
             # Message and subject
             library_id: Optional[str] = None, message_id: str, subject_id: str,
             # Email headers
             from_email: str = DEFAULT_FROM_EMAIL, from_name: str = DEFAULT_FROM_NAME,
             reply_to: str = DEFAULT_REPLY_TO,
             # Survey link
             link_type: str = LINK_INDIVIDUAL,
             link_expiration_date: Optional[datetime] = None):
        """Send an email distribution to a transaction batch"""

        # Sensible defaults
        send_date = send_date or datetime.now()
        link_expiration_date = link_expiration_date or send_date + timedelta(days=DEFAULT_LINK_EXPIRATION_DAYS)
        library_id = library_id or self.client.library_id

        spec = _email_distribution_spec(from_email=from_email, from_name=from_name, reply_to=reply_to,
                                        subject_id=subject_id, library_id=library_id, message_id=message_id,
                                        batch_id=batch_id, survey_id=survey_id,
                                        link_expiration_date=link_expiration_date, link_type=link_type,
                                        send_date=send_date)
        return self.create(json_data=spec)

    def links(self, qx_id, survey_id):
        query_data = {'surveyId': survey_id}
        path = _urljoin(self.path, f"{qx_id}/links")
        return self.client.list(path, query_data=query_data)

    def history(self, dist_id):
        path = _urljoin(self.path, f'{dist_id}/history')
        return self.client.list(path)

    def list(self, *, survey_id, list_id=None):
        # TODO Support all available filters
        query_data = {'surveyId': survey_id}
        if list_id:
            query_data['mailingListId'] = list_id
        return super().list(query_data=query_data)


# TODO Support sending to mailing list
def _sms_distribution_spec(*, name: str, survey_id: str, batch_id: str,
                           library_id: str, message_id: str,
                           send_date: datetime) -> dict:
    spec = {
            "name": name,
            "surveyId": survey_id,
            "method": "Invite",
            "message": {
                "messageId": message_id,
                "libraryId": library_id
            },
            "sendDate": format_datetime(send_date),
            "recipients": {
                "transactionBatchId": batch_id
            }
    }
    return spec


def _single_sms_distribution_spec(*, name: str, survey_id: str, message: str,
                                  mailinglist_id: str, send_date: datetime) -> dict:
    spec = {
        "name": name,
        "surveyId": survey_id,
        "method": "Invite",
        "message": {
            "messageText": message,
        },
        "sendDate": format_datetime(send_date),
        "recipients": {
            "mailingListId": mailinglist_id,
        }
    }
    return spec


class SMSDistributionManager(BaseManager):
    path_spec = "distributions/sms"

    def get(self, qx_id, *, survey_id):
        query_data = {"surveyId": survey_id}
        return super().get(qx_id, query_data=query_data)

    def send(self, *, name: str, survey_id: str, batch_id: str,
             library_id: Optional[str] = None, message_id: str,
             send_date: Optional[datetime] = None):
        library_id = library_id or self.client.library_id
        send_date = send_date or datetime.now()
        spec = _sms_distribution_spec(name=name, survey_id=survey_id, batch_id=batch_id,
                                      library_id=library_id, message_id=message_id,
                                      send_date=send_date)
        return self.create(json_data=spec)

    def send_single(self, *, name: str, survey_id: str, message: str,
                    mailinglist_id: str, send_date: Optional[datetime] = None):
        send_date = send_date or datetime.now()
        spec = _single_sms_distribution_spec(
            name=name,
            survey_id=survey_id,
            message=message,
            mailinglist_id=mailinglist_id,
            send_date=send_date,
        )
        return self.create(json_data=spec)

    def stats(self, qx_id, survey_id):
        """Global SMS distribution stats

          Example:
          {
            'sent': 0,
            'started': 1,
            'finished': 1,
            'failed': 0,
            'credits": 0,
          }
        """
        data = self.get(qx_id, survey_id=survey_id)
        return data.get('stats')

# Messages
# --------


class MessageManager(BaseManager):
    path_spec = "libraries/{library_id}/messages"

    EMAIL = 'invite'
    EMAIL_SUBJECT = 'emailSubject'
    SMS = 'smsInvite'
    CATEGORIES = (EMAIL, EMAIL_SUBJECT, SMS)

    def list(self, *, num_pages=None, category=None, offset=0):
        query_data = {'offset': offset}
        if category is not None:
            if category not in MessageManager.CATEGORIES:
                raise ValueError(f"Category must be one of: {', '.join(MessageManager.CATEGORIES)}")
            query_data['category'] = category
        return super().list(num_pages=num_pages, query_data=query_data)

# Surveys
# -------


class SurveyManager(BaseManager):
    path_spec = "surveys/"

# Transactions
# ------------


class TransactionBatchManager(BaseManager):
    path_spec = "directories/{directory_id}/transactionbatches"

    def create(self, transaction_ids=None, created_date=None):
        if transaction_ids is None:
            transaction_ids = []
        spec = {
            'transactionIds': transaction_ids,
            'createdDate': format_datetime(created_date)
        }
        return super().create(json_data=spec)

    def transactions(self, batch_id, page_size=MAX_PAGE_SIZE):
        """List transactions in a given batch"""
        path = _urljoin(self.path, batch_id, 'transactions')
        query_data = {'pageSize': page_size}
        return self.client.list(path, query_data=query_data)


class TransactionManager(BaseManager):
    path_spec = "directories/{directory_id}/transactions"

# Directories
# -----------


class DirectoryManager(BaseManager):
    path_spec = "directories"

    # Not supported by Qualtrics
    create = None
    get = None
    update = None
    delete = None

    def list(self, *, query_data=None, num_pages=None):
        query_data = query_data or {}
        query_data['useNewPaginationScheme'] = 'true'
        return super().list(query_data=query_data, num_pages=num_pages)


# Directory contacts
# __________________
class DirectoryContactManager(BaseManager):
    path_spec = "directories/{directory_id}/contacts"

    HISTORY_TYPE_EMAIL = 'email'

    def list(self, *, page_size=MAX_PAGE_SIZE, num_pages=None):
        query_data = {"pageSize": page_size}
        return super().list(num_pages=num_pages, query_data=query_data)

    def transactions(self, qx_id: str, page_size: Optional[int] = MAX_PAGE_SIZE, **kwargs):
        query_data = {"pageSize": page_size}
        path = _urljoin(self.path, qx_id, 'transactions')
        return self.client.list(path, query_data=query_data, **kwargs)

    def history(self, qx_id: str, history_type: Optional[str] = HISTORY_TYPE_EMAIL, **kwargs):
        path = _urljoin(self.path, qx_id, 'history')
        query_data = {'type': history_type}
        return self.client.list(path, query_data=query_data, **kwargs)


# Shortcuts
# ---------
_client = None


def default_client(session=None):
    """Client instance built from Django settings"""
    global _client

    if _client is None:
        _client = XMDirectory(
            api_key=settings.QXSMS_API_KEY,
            domain=settings.QXSMS_QX_DOMAIN,
            directory_id=settings.QXSMS_DIRECTORY_ID,
            library_id=settings.QXSMS_LIBRARY_ID,
            session=session
        )
    return _client


# Bound managers
# --------------
def directory_contacts():
    xm = default_client()
    return xm.directory_contacts


def contact_imports(list_id):
    xm = default_client()
    return xm.contact_imports(list_id)


def mailing_lists():
    xm = default_client()
    return xm.mailing_lists


def mailing_list_contacts(list_id):
    xm = default_client()
    return xm.mailing_list_contacts(list_id)


def distributions():
    xm = default_client()
    return xm.distributions


def sms_distributions():
    xm = default_client()
    return xm.sms_distributions


def transaction_batches():
    xm = default_client()
    return xm.transaction_batches


def messages():
    xm = default_client()
    return xm.messages


# Listings
# -------------
def list_mailing_lists():
    xm = default_client()
    return xm.mailing_lists.list()


def list_surveys():
    xm = default_client()
    return xm.surveys.list()


def list_messages(category=None):
    xm = default_client()
    return xm.messages.list(category=category)


def list_distributions(survey_id, list_id=None):
    xm = default_client()
    return xm.distributions.list(survey_id=survey_id, list_id=list_id)


def list_distribution_links(qx_id, qx_survey_id):
    xm = default_client()
    return xm.distributions.links(qx_id, qx_survey_id)


def list_directory_contacts(*, page_size=MAX_PAGE_SIZE, num_pages=None):
    xm = default_client()
    return xm.directory_contacts.list(page_size=page_size, num_pages=num_pages)


def list_contacts(list_id, *, page_size=MAX_PAGE_SIZE, num_pages=None):
    xm = default_client()
    return xm.mailing_list_contacts(list_id).list(page_size=page_size, num_pages=num_pages)


def create_transaction_batch() -> str:
    tbm = transaction_batches()
    return tbm.create()


def create_mailing_list(name: str) -> str:
    mlm = mailing_lists()
    return mlm.create(name)


def import_contacts(*, list_id: str, contacts: list[dict], batch_id: Optional[str] = None) -> str:
    cim = contact_imports(list_id)
    return cim.start_import(contacts=contacts, batch_id=batch_id)


def generate_links(*, survey_id: str, list_id: str, expiration_date: datetime, description: str) -> str:
    dm = distributions()
    return dm.generate_links(survey_id=survey_id, expiration_date=expiration_date,
                             description=description, list_id=list_id)
