# -- STDLIB
import logging

# -- DJANGO
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import generic

# -- QXSMS (LOCAL)
from . import forms, services, tasks
from .forms import LinkDistributionGenerateForm
from .models import LinkDistribution, MessageDistribution
from .tasks import create_message_distribution

logger_name = __name__
if settings.DEBUG:
    logger_name = 'django.server'
# TODO Configure logger
logger = logging.getLogger(logger_name)


class LinkDistributionCreate(generic.CreateView):
    template_name = 'distributions/create.html'
    form_class = forms.LinkDistributionForm
    success_url = reverse_lazy('dist:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        skip_cache = 'nocache' in self.request.GET
        kwargs['surveys'] = services.get_surveys(skip_cache=skip_cache)
        return kwargs


class LinkDistributionDetail(generic.DetailView):
    queryset = LinkDistribution.objects.annotate(Count('link'))
    template_name = 'distributions/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.qx_id is not None:
            context['stats'] = self.get_stats()
        return context

    def get_stats(self):
        skip_cache = 'nocache' in self.request.GET
        stats = services.get_distribution_stats(qx_id=self.object.qx_id, survey_id=self.object.survey_id,
                                                skip_cache=skip_cache)
        # Qualtrics counts 'finished' answers as a subset of 'started'
        stats['in_progress'] = stats['started'] - stats['finished']
        return stats


class LinkDistributionHistory(generic.detail.SingleObjectMixin, generic.ListView):
    template_name = 'distributions/history.html'

    def get(self, request, *args, **kwargs):
        qs = LinkDistribution.objects.filter(qx_id__isnull=False).annotate(Count('link'))
        self.object = super().get_object(queryset=qs)
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return self.object.links.select_related('profile__panel')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        skip_cache = 'nocache' in self.request.GET
        history = services.get_distribution_history(qx_id=self.object.qx_id, skip_cache=skip_cache)
        links = context['object_list']
        history_links = services.merge_links_and_history(links, history)
        context['records_stats'] = services.history_links_stats(history_links)
        return context


class LinkDistributionGenerate(generic.UpdateView):
    template_name = 'distributions/generate.html'
    form_class = LinkDistributionGenerateForm
    queryset = LinkDistribution.objects.all()
    if not settings.DEBUG:
        queryset = queryset.filter(qx_id__isnull=True)

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.save_links()
        tasks.create_link_distribution.delay(dist_id=self.object.pk)
        return response


class LinkDistributionList(generic.ListView):
    template_name = 'distributions/list.html'
    queryset = LinkDistribution.objects.select_related('survey')


class LinkDistributionDelete(generic.DeleteView):
    template_name = "distributions/delete.html"
    model = LinkDistribution
    success_message = None

    def get_queryset(self):
        return super().get_queryset().filter(expiration_date=None)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, self.success_message)
        return response


# Message distributions
# ---------------------


class MessageDistributionList(generic.ListView):
    template_name = "distributions/msgd/list.html"

    def get_queryset(self):
        related = (
            'link_distribution',
            'subject',
            'message',
            'fallback',
        )
        kwargs = {
            'fallback_of__isnull': True,
        }
        return MessageDistribution.objects.filter(**kwargs).select_related(*related)


class BaseMessageDistributionCreate(generic.CreateView):
    template_name = 'distributions/msgd/create.html'
    success_url = reverse_lazy('dist:msgd:list')

    def dispatch(self, request, *args, **kwargs):
        skip_cache = 'nocache' in self.request.GET
        self.messages = services.get_messages(skip_cache=skip_cache)
        return super().dispatch(request, *args, **kwargs)


class EmailDistributionCreate(BaseMessageDistributionCreate):
    form_class = forms.EmailDistributionForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['messages'] = services.filter_email_messages(self.messages)
        kwargs['subjects'] = services.filter_email_subjects(self.messages)
        return kwargs


class SMSDistributionCreate(BaseMessageDistributionCreate):
    form_class = forms.SMSDistributionForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['messages'] = services.filter_sms_messages(self.messages)
        return kwargs


class MessageDistributionFallbackCreate(generic.detail.SingleObjectMixin, generic.FormView):
    template_name = "distributions/msgd/fallback_create.html"
    form_class = forms.QxMessageForm

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        """Redirect to parent distribution's detail view"""
        return reverse('dist:msgd:detail', args=[self.object.pk])

    def get_queryset(self):
        """Only distributions that do not already have a fallback, and are not themselves a fallback"""
        kwargs = {
            'fallback__isnull': True,
            'fallback_of__isnull': True,
            'send_date__isnull': True,
        }
        return MessageDistribution.objects.filter(**kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        skip_cache = 'nocache' in self.request.GET
        messages = services.get_messages(skip_cache=skip_cache)
        if self.object.is_email:
            kwargs['messages'] = services.filter_sms_messages(messages)
        else:
            kwargs['messages'] = services.filter_email_messages(messages)
            kwargs['subjects'] = services.filter_email_subjects(messages)
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            message, subject = form.save()
            self.object.add_fallback(message=message, subject=subject)
        return super().form_valid(form)


class MessageDistributionSend(generic.UpdateView):
    form_class = forms.MessageDistributionSendForm
    template_name = 'distributions/msgd/send.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['send_date'] = timezone.now()
        return initial

    def get_queryset(self):
        filters = {
            'send_date__isnull': True,
            'fallback_of__isnull': True
        }
        return MessageDistribution.objects.filter(**filters)

    def get_form_kwargs(self):
        """ Passes the history to form"""
        kwargs = super().get_form_kwargs()
        kwargs['history'] = self.get_history()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['candidates_stat'] = self.object.get_candidates_stats(self.get_history())
        return context

    def get_history(self):
        skip_cache = 'nocache' in self.request.GET
        qx_id = self.object.link_distribution.qx_id
        return services.get_distribution_history(qx_id=qx_id, skip_cache=skip_cache)

    def form_valid(self, form):
        response = super().form_valid(form)
        # Freeze the set of recipients
        history = self.get_history()
        self.object.save_links(history=history)
        create_message_distribution.delay(self.object.pk)
        if self.object.has_fallback:
            self.object.fallback.save_links(history=history)
            create_message_distribution.delay(self.object.fallback.pk)
        return response


class MessageDistributionDetail(generic.DetailView):
    template_name = "distributions/msgd/detail.html"
    queryset = MessageDistribution.objects.annotate(Count('links'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        skip_cache = 'nocache' in self.request.GET
        if self.object.qx_id is not None:
            context['stats'] = services.get_distribution_stats(qx_id=self.object.qx_id,
                                                               survey_id=settings.QXSMS_SEND_SURVEY,
                                                               skip_cache=skip_cache,
                                                               is_sms=self.object.is_sms)
        return context


class MessageDistributionUpdate(generic.UpdateView):
    model = MessageDistribution
    template_name = "distributions/msgd/update.html"
    fields = ['description']

    def get_object(self):
        response = super().get_object()
        if response.is_fallback:
            return reverse_lazy('dist:msgd:list')
        return response

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.object.has_fallback:
            self.object.fallback.description = form.cleaned_data['description']
            self.object.fallback.save()
        return response


class MessageDistributionDelete(generic.DeleteView):
    template_name = "distributions/msgd/delete.html"
    model = MessageDistribution

    def get_queryset(self):
        return super().get_queryset().filter(qx_id=None, qx_created_date=None,
                                             send_date=None, fallback_of__send_date=None)
