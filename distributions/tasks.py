# -- DJANGO
from django.conf import settings
from django.core.mail import mail_admins
from django.utils import timezone

# -- THIRDPARTY
from celery import Task, shared_task
from celery.utils.log import get_task_logger

# -- QXSMS (LOCAL)
from . import client, models, services
from .client import QxClientError

# TODO Add formatter that prefixes logs with distribution short uid
logger = get_task_logger(__name__)


class ImportInProgress(Exception):
    pass


class BaseTask(Task):
    autoretry_for = (client.QxServerError,)
    max_retries = 10
    retry_backoff = 8
    retry_jitter = False

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if isinstance(exc, QxClientError):
            traceback = str(einfo)
            logger.error(traceback)
            mail_admins("Task error", traceback)


def _check_import_status(*, list_id, import_id):
    if not (list_id and import_id):
        raise RuntimeError(f"list and import QX_IDs needed to track import progress. "
                           f"Got {list_id}, {import_id}")
    ci = client.contact_imports(list_id)
    pct = ci.progress(import_id)
    if pct < 100:
        logger.info("mailing_list_id:%s import_id:%s progress:%d%%", list_id, import_id, pct)
        raise ImportInProgress
    return pct


@shared_task(base=BaseTask)
def create_distribution_list(dist_id):
    """Create a mailing list for the purpose of generating links

    The name of the mailing list is set to the the distribution's short UID.
    """
    dist = models.LinkDistribution.objects.get(pk=dist_id)
    if dist.qx_list_id:
        logger.info('LinkDistribution %s: using existing list %s', dist.short_uid, dist.qx_list_id)
    else:
        logger.info("LinkDistribution %s: creating mailing list)", dist.short_uid)
        dist.qx_list_id = client.create_mailing_list(dist.short_uid)
        dist.save()
    return dist_id


@shared_task(base=BaseTask)
def start_contact_import(dist_id: str, message_distribution=False) -> tuple[str, str, str]:
    """Import contacts in the distribution's mailing list"""
    if message_distribution:
        manager = models.MessageDistribution.objects
    else:
        manager = models.LinkDistribution.objects
    dist = manager.get(pk=dist_id)
    if dist.qx_import_id:
        logger.info('%s %s: using existing import %s', dist.__class__, dist.short_uid, dist.qx_import_id)
    else:
        logger.info("%s %s: starting import", dist.__class__, dist.short_uid)
        dist.qx_import_id = client.import_contacts(**dist.get_import_kwargs())
        dist.save()
    return dist_id, dist.qx_list_id, dist.qx_import_id


@shared_task(base=BaseTask, autoretry_for=(ImportInProgress, client.QxServerError))
def wait_until_import_completes(import_spec: tuple[str, str, str]) -> str:
    dist_id, list_id, import_id = import_spec
    _check_import_status(list_id=list_id, import_id=import_id)
    return dist_id


@shared_task(base=BaseTask)
def generate_links(dist_id):
    """Generate survey links for a distribution bound to a mailing list

    This task assumes that a mailing list has been created and populated for
    the given distribution.
    """
    dist = models.LinkDistribution.objects.get(pk=dist_id)
    if dist.qx_id:
        logger.info('LinkDistribution %s: using existing links %s', dist.short_uid, dist.qx_id)
    else:
        logger.info("LinkDistribution %s: generating links...", dist.short_uid)
        dist.qx_id = client.generate_links(
            survey_id=dist.survey.qx_id,
            expiration_date=dist.expiration_date,
            list_id=dist.qx_list_id,
            description=dist.description
        )
        dist.qx_created_date = timezone.now()
        dist.save()
    return dist_id


@shared_task(base=BaseTask)
def update_links(dist_id):
    """Retrieve distribution links and save Link instances"""
    dist = models.LinkDistribution.objects.get(pk=dist_id)
    qx_links = services.list_distribution_links(qx_id=dist.qx_id, survey_id=dist.survey_id, skip_cache=True)
    updated, skipped = dist.update_links(qx_links)
    n_updated, n_skipped = len(updated), len(skipped)
    logger.info("LinkDistribution %s: updated %d skipped %d",
                dist.short_uid, n_updated, n_skipped)
    return n_updated, n_skipped


# Task chain used to generate and save distribution links
create_link_distribution = (
    create_distribution_list.s() |
    start_contact_import.s() |
    wait_until_import_completes.signature(countdown=5) |
    generate_links.s() |
    update_links.s()
)


# Message distributions
# ---------------------
@shared_task(base=BaseTask)
def create_transaction_batch(dist_id: str) -> str:
    dist = models.MessageDistribution.objects.get(pk=dist_id)
    if dist.qx_batch_id:
        logger.warning("MessageDistribution %s: using existing batch %s", dist.short_uid, dist.qx_batch_id)
    else:
        logger.warning("MessageDistribution %s: creating transaction batch", dist.short_uid)
        dist.qx_batch_id = client.create_transaction_batch()
        dist.save()
    return dist_id


@shared_task(base=BaseTask)
def send_message_distribution(dist_id: str) -> str:
    dist = models.MessageDistribution.objects.get(pk=dist_id)
    kwargs = {
        'batch_id': dist.qx_batch_id,
        'survey_id': settings.QXSMS_SEND_SURVEY,
        'message_id': dist.message_id,
        'send_date': dist.get_send_date(),
    }
    if dist.contact_mode == models.MessageDistribution.MODE_EMAIL:
        dm = client.distributions()
        kwargs['subject_id'] = dist.subject_id
    else:
        dm = client.sms_distributions()
        kwargs['name'] = f"{dist.short_uid}"
    dist.qx_id = dm.send(**kwargs)
    dist.qx_created_date = timezone.now()
    dist.save()
    logger.info("MessageDistribution %s: %s distribution %s sent!",
                dist.short_uid, dist.get_contact_mode_display(), dist.qx_id)
    return dist.qx_id


create_message_distribution = (
    create_transaction_batch.s() |
    start_contact_import.s(message_distribution=True) |
    wait_until_import_completes.signature(countdown=5) |
    send_message_distribution.s()
)
