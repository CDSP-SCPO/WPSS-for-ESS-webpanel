# -- STDLIB
import csv
import logging
from datetime import datetime, timezone

# -- DJANGO
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import (
    HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, TemplateView
from django.views.generic.base import View
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import (
    BaseFormView, CreateView, DeleteView, FormView, UpdateView,
)

# -- THIRDPARTY
from django_filters.views import FilterView

# -- QXSMS
from distributions import models as distmodels, services, views as distviews
from hq.forms import (
    ManagerAddMultipleForm, ManagerCreateForm, ManagerUpdateForm,
    PanelCreateForm, PanelUpdateForm,
)
from hq.models import Panel, SMSStats
from manager.filters import MessageDeliveryReportFilter
from manager.forms import BlankSlotImportForm
from panelist.models import BlankSlot, Profile
from qxauth.forms import UserUpdateForm
from qxsms import settings
from utils.csvimport import BlankSlotValueResource, ProfileHQResource
from utils.utils import get_panelist_counts
from utils.views import (
    BaseBlankSlotValueList, BaseBlankSlotValueUpdate, csv_response,
)

# -- QXSMS (LOCAL)
from .filters import PanelistsHqFilter

User = get_user_model()

logger = logging.getLogger(__name__)
if settings.DEBUG:
    logger = logging.getLogger('django.server')


class AddRelatedView(SingleObjectMixin, BaseFormView):
    """ Generic view to add a related entity to a model.

    form_class must be a subclass of AddRelatedForm.
    """
    success_view_name = None
    form_class = None
    object = None

    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(permitted_methods=('POST',))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.object
        return kwargs

    def get_success_url(self):
        return reverse(self.success_view_name, args=(self.object.pk,))

    def form_invalid(self, form):
        return HttpResponseRedirect(self.get_success_url())

    def form_valid(self, form):
        owner_attr = form.owner_attr
        related = form.cleaned_data[owner_attr]
        getattr(self.object, owner_attr).add(*related)
        return HttpResponseRedirect(self.get_success_url())


class Home(TemplateView):
    template_name = 'hq/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'panelist_count': Profile.objects.count(),
            'panel_count': Panel.objects.count(),
            'manager_count': User.objects.filter(groups__name=settings.QXSMS_GROUP_MANAGERS).count(),
        })
        return context


# Hq
class HqProfileUpdate(SuccessMessageMixin, UpdateView):
    template_name = 'hq/profile_update.html'
    form_class = UserUpdateForm
    success_url = reverse_lazy('hq:home')
    success_message = _("Your personal information has been updated")

    def get_object(self, **kwargs):
        return self.request.user


# Managers
class ManagerList(ListView):
    queryset = User.objects.filter(groups__name=settings.QXSMS_GROUP_MANAGERS).annotate(panel_count=Count('panel'))
    template_name = 'hq/manager_list.html'


class ManagerCreate(SuccessMessageMixin, CreateView):
    form_class = ManagerCreateForm
    template_name = 'hq/manager_create.html'
    success_url = reverse_lazy('hq:manager-list')
    success_message = _("Created national coordinator account %(email)s")

    def form_valid(self, form):
        response = super().form_valid(form)
        form.instance.send_welcome(request=self.request)
        return response


class ManagerUpdate(SuccessMessageMixin, UpdateView):
    form_class = ManagerUpdateForm
    template_name = 'hq/manager_update.html'
    success_url = reverse_lazy('hq:manager-list')
    success_message = _("Updated national coordinator account %(email)s")

    def get_queryset(self):
        return User.objects.filter(groups__name=settings.QXSMS_GROUP_MANAGERS)


class ManagerDelete(DeleteView):
    template_name = 'hq/manager_confirm_delete.html'
    success_url = reverse_lazy('hq:manager-list')

    def get_queryset(self):
        return User.objects.filter(groups__name=settings.QXSMS_GROUP_MANAGERS)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(self.request, _(
            "Deleted national coordinator account %s"
        ) % self.object.email)
        return response


# Distributions
###############
class LinkDistributionList(distviews.LinkDistributionList):
    template_name = 'hq/dist/list.html'


class LinkDistributionCreate(distviews.LinkDistributionCreate):
    template_name = "hq/dist/create.html"
    success_url = reverse_lazy('hq:link-distribution-list')


class LinkDistributionDetail(distviews.LinkDistributionDetail):
    template_name = "hq/dist/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.qx_id:
            skip_cache = 'nocache' in self.request.GET
            history = services.get_distribution_history(qx_id=self.object.qx_id, skip_cache=skip_cache)
            links = self.object.links.exclude(url='')
            history_links = services.merge_links_and_history(links, history)
            stats = services.history_links_stats(history_links)

            # Total check
            for p in stats:
                if stats[p]["not_started"] + stats[p]["started"] + stats[p]["finished"] + stats[p]["failed"]\
                        + stats[p]["partially_finished"] != stats[p]["total"]:
                    error_message = f"panel '{p}' : {stats[p]['not_started']} + {stats[p]['started']} + " \
                                    f"{stats[p]['finished']} + {stats[p]['failed']} + " \
                                    f"{stats[p]['partially_finished']} != {stats[p]['total']}"
                    logger.error(error_message)

            context['records_stats'] = stats
        return context


class LinkDistributionDelete(distviews.LinkDistributionDelete):
    template_name = "hq/dist/delete.html"
    success_url = reverse_lazy('hq:link-distribution-list')
    success_message = _("Deleted set of individual links")


class LinkDistributionGenerate(distviews.LinkDistributionGenerate):
    template_name = "hq/dist/generate.html"

    def get_success_url(self):
        return reverse('hq:link-distribution-detail', args=[self.object.pk])


class MessageDistributionList(distviews.MessageDistributionList):
    template_name = "hq/msgdist/list.html"
    paginate_by = 25


def download_sms_stats(request, pk):
    filename = f"stats_sms_{distmodels.MessageDistribution.objects.get(pk=pk).short_uid}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.DictWriter(response, fieldnames=["Panelist ID", "Panel", "Status", "Bounce Reason",
                                                  "Last status update"])

    writer.writeheader()
    for stat in SMSStats.objects.filter(msgdist_id=pk):
        writer.writerow({"Panelist ID": stat.panelist.panelist_id, "Panel": stat.panelist.panel.name,
                         "Status": stat.smsstatus, "Bounce Reason": stat.bouncereason,
                         "Last status update": stat.datefile})

    return response


class MessageDistributionDetail(DetailView):
    template_name = "hq/msgdist/detail.html"
    queryset = distmodels.MessageDistribution.objects.annotate(Count('links'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.qx_id is None:
            return context
        skip_cache = 'nocache' in self.request.GET

        # Include global stats if we have an SMS
        if self.object.is_sms:
            statssms = SMSStats.objects.filter(msgdist=self.object)
            context['detailedstatssms'] = statssms
            stats = services.get_distribution_stats(qx_id=self.object.qx_id,
                                                    survey_id=settings.QXSMS_SEND_SURVEY,
                                                    skip_cache=skip_cache,
                                                    is_sms=True)
        # For emails, include stats aggregated by panel
        else:
            history = services.get_distribution_history(qx_id=self.object.qx_id, skip_cache=skip_cache)
            links = self.object.links.select_related('profile__panel')
            links_with_history = services.merge_links_and_history(links, history)
            stats = services.msg_distributions_stats(links_with_history)

        context['schedule'] = False
        if datetime.now(timezone.utc) < self.object.get_send_date():
            context['schedule'] = True
            context['days'] = (self.object.get_send_date() - datetime.now(timezone.utc)).days

        context['stats'] = stats
        return context


class MessageDistributionDelete(distviews.MessageDistributionDelete):
    template_name = "hq/msgdist/delete.html"
    success_message = _("Deleted message distribution")

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, self.success_message)
        return response

    def get_success_url(self):
        # In case of a fallback, redirect to the parent's detail view
        if self.object.is_fallback:
            return reverse('hq:msg-distribution-detail', args=[self.object.fallback_of.pk])
        return reverse('hq:msg-distribution-list')


class EmailDistributionCreate(distviews.EmailDistributionCreate):
    template_name = "hq/msgdist/create.html"
    success_url = reverse_lazy('hq:msg-distribution-list')


class SMSDistributionCreate(distviews.SMSDistributionCreate):
    template_name = "hq/msgdist/create.html"
    success_url = reverse_lazy('hq:msg-distribution-list')


class MessageDistributionSend(distviews.MessageDistributionSend):
    template_name = "hq/msgdist/send.html"

    def get_success_url(self):
        return reverse('hq:msg-distribution-detail', args=[self.object.pk])


class MessageDistributionUpdate(distviews.MessageDistributionUpdate):
    template_name = "hq/msgdist/update.html"

    def get_success_url(self):
        return reverse('hq:msg-distribution-detail', args=[self.object.pk])


class MessageDistributionHistory(SingleObjectMixin, FilterView):
    template_name = "hq/msgdist/history.html"
    filterset_class = MessageDeliveryReportFilter
    paginated_by = 25

    def get(self, request, *args, **kwargs):
        self.object = super().get_object(queryset=distviews.MessageDistribution.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        panel = get_object_or_404(Panel, pk=self.kwargs.get('panel_pk'))
        return self.object.links.filter(profile__panel=panel).select_related('profile__panel')

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        skip_cache = 'nocache' in self.request.GET
        self.history = services.get_distribution_history(qx_id=self.object.qx_id, skip_cache=skip_cache)
        kwargs['history'] = self.history
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = get_object_or_404(Panel, pk=self.kwargs.get('panel_pk'))
        skip_cache = 'nocache' in self.request.GET
        profile_ids = [qs.profile.id for qs in context['object_list']]
        context['counts'] = get_panelist_counts(Profile.objects.filter(id__in=profile_ids),
                                                grand_total_present=self.get_queryset().count())

        links = context['object_list']
        context['object_list'] = services.merge_links_and_history(links, self.history)
        context['records_stats'] = services.msg_distributions_stats(context['object_list'])

        paginator = Paginator(context['object_list'], self.paginated_by)
        page = self.request.GET.get('page')
        context['profiles'] = paginator.get_page(page)
        if self.object.is_sms:
            stats = services.get_distribution_stats(qx_id=self.object.qx_id,
                                                    survey_id=settings.QXSMS_SEND_SURVEY,
                                                    skip_cache=skip_cache,
                                                    is_sms=True)
        else:
            stats = services.msg_distributions_stats(context['object_list'])

        context['stats'] = stats

        return context


class MessageDistributionFallbackCreate(distviews.MessageDistributionFallbackCreate):
    template_name = "hq/msgdist/fallback_create.html"

    def get_success_url(self):
        """Redirect to parent distribution's detail view"""
        return reverse('hq:msg-distribution-detail', args=[self.object.pk])


# Panels
class PanelList(ListView):
    queryset = Panel.objects.annotate(
        manager_count=Count('managers', distinct=True),
        profile_count=Count('profile', distinct=True)
    )
    template_name = 'hq/panel_list.html'


class PanelCreate(SuccessMessageMixin, CreateView):
    """Create a panel, and corresponding Qualtrics contact list.

    At least one panel manager must be specified in order to create a panel.
    """

    form_class = PanelCreateForm
    template_name = 'hq/panel_create.html'
    success_url = reverse_lazy('hq:panel-list')

    def get_success_message(self, cleaned_data):
        success_message = f"Created panel {cleaned_data['name']}"
        managers_str = ' '.join(str(manager) for manager in cleaned_data['managers'])
        if managers_str:
            success_message = f"{success_message} managed by {managers_str}"
        return success_message


class PanelUpdate(SuccessMessageMixin, UpdateView):
    model = Panel
    form_class = PanelUpdateForm
    template_name = 'hq/panel_update.html'
    success_message = _("Updated Panel")

    def get_success_url(self):
        return reverse('hq:panel-detail',  args=[self.object.pk])


class PanelDetail(DetailView):
    template_name = 'hq/panel_detail.html'

    def get_queryset(self):
        return Panel.objects.annotate(
            manager_count=Count('managers', distinct=True),
            member_count=Count('profile', distinct=True),
            link_set_count=Count('distributions')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assignment_form'] = ManagerAddMultipleForm(owner=self.object)
        return context


class PanelManagerAssign(SuccessMessageMixin, AddRelatedView):
    form_class = ManagerAddMultipleForm
    success_view_name = 'hq:panel-detail'
    success_message = _("Assigned manager(s) %(managers_str)s")

    def get_queryset(self):
        return Panel.objects.prefetch_related('managers')

    def get_success_message(self, cleaned_data):
        cleaned_data['managers_str'] = ", ".join([str(m) for m in cleaned_data['managers']])
        return super().get_success_message(cleaned_data)


class PanelManagerUnassign(SingleObjectMixin, View):
    model = Panel
    object = None
    success_message = _("Unassigned manager %(email)s")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        user_id = request.POST.get('manager')
        user = get_object_or_404(self.object.managers.all(), pk=user_id)
        self.object.managers.remove(user)
        messages.success(self.request, self.success_message % {'email': user.email})
        return HttpResponseRedirect(reverse('hq:panel-detail', args=(self.object.pk,)))


# Surveys
class SurveyList(TemplateView):
    template_name = 'hq/survey_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['survey_list'] = self.get_surveys()
        return context

    def get_surveys(self):
        skip_cache = 'nocache' in self.request.GET
        surveys = services.get_surveys(skip_cache=skip_cache)
        return [s for s in surveys if s['id'] != settings.QXSMS_SEND_SURVEY]


class PanelmemberList(FilterView):
    template_name = 'hq/panel_member_list.html'
    filterset_class = PanelistsHqFilter
    paginate_by = 25

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['counts'] = get_panelist_counts(self.object_list)
        context["language_codes"] = self.object_list.values_list("language", flat=True).order_by("language").distinct()
        return context


class BlankSlotList(ListView):
    template_name = 'hq/blankslot_list.html'
    model = BlankSlot


class BlankSlotCreate(SuccessMessageMixin, CreateView):
    model = BlankSlot
    fields = '__all__'
    template_name = 'hq/blankslot_create.html'
    success_url = reverse_lazy('hq:blankslot-list')
    success_message = _("Created blank slot %(name)s")


class BlankSlotUpdate(SuccessMessageMixin, UpdateView):
    model = BlankSlot
    fields = ['description']
    template_name = 'hq/blankslot_update.html'
    success_url = reverse_lazy('hq:blankslot-list')
    success_message = "Updated blank slot"


class BlankSlotDelete(DeleteView):
    """Delete blank slot"""
    success_url = reverse_lazy('hq:blankslot-list')
    template_name = "hq/blankslot_confirm_delete.html"
    model = BlankSlot

    def delete(self, request, *args, **kwargs):
        blankslot = self.get_object()
        name = blankslot.name
        response = super().delete(request, *args, **kwargs)
        messages.success(self.request, _("Deleted blank slot %s") % name)
        return response


class ProfileExportCSV(View):

    def get(self, request, *args, **kwargs):
        dataset = ProfileHQResource().export()
        response = csv_response(dataset.csv, 'export-panelist-data')
        return response


class BlankSlotValueUpdate(BaseBlankSlotValueUpdate):
    template_name = 'hq/blankslot_value_formset.html'

    def get_success_url(self):
        return reverse('hq:blankslotvalue-list', args=[self.object.pk])


class BlankSlotValueList(BaseBlankSlotValueList):
    template_name = "hq/blankslot_value_list.html"


class BlankSlotImportCsv(FormView):
    template_name = 'hq/blankslot_value_import.html'
    success_message = _("{new} additional variables created.\n{update} additional variables updated.\n{skip} rows "
                        "skipped")
    result = None

    def get_form_class(self):
        return BlankSlotImportForm

    def get_success_url(self):
        return reverse('hq:panelmember-list')

    def get_resource(self):
        return BlankSlotValueResource()

    def form_valid(self, form):
        resource = self.get_resource()
        dataset = form.cleaned_data["dataset"]
        self.result = res = resource.import_data(dataset, dry_run=True)

        if res.has_errors() or res.has_validation_errors():
            return self.form_invalid(form)

        self.result = resource.import_data(dataset, dry_run=False)

        success_message = self.success_message.format(**self.result.totals)
        messages.success(self.request, success_message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['result'] = self.result
        return context


class MessageList(ListView):
    template_name = "hq/message_list.html"

    def get_queryset(self):
        return services.get_messages()
