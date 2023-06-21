# -- STDLIB
import csv
from datetime import MINYEAR, datetime, timezone

# -- DJANGO
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.base import RedirectView, View
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import (
    CreateView, DeleteView, FormView, UpdateView,
)

# -- THIRDPARTY
from django_filters.views import FilterView

# -- QXSMS
from distributions import services, views as distviews
from distributions.models import MessageDistribution
from hq.models import Panel, SMSStats
from hq.views import BlankSlotImportCsv
from panelist.forms import ProfileForm
from panelist.models import Profile
from qxauth.forms import UserUpdateForm
from qxauth.views import PasswordReset
from qxsms import settings
from utils.context_processors import get_instance_name
from utils.csvimport import BlankSlotValueResource, ProfileResource
from utils.translation import lng_to_country
from utils.utils import get_panelist_counts
from utils.views import (
    BaseBlankSlotValueList, BaseBlankSlotValueUpdate, csv_response,
)

# -- QXSMS (LOCAL)
from .api import get_task_info
from .filters import (
    IndividualLinksFilter, MessageDeliveryReportFilter, PanelMemberFilter,
)
from .forms import CSVImportForm, PanelUpdateForm, SelectExportForm
from .models import GroupTaskImport
from .tasks import import_data_celery


class ManagerProfileUpdate(SuccessMessageMixin, UpdateView):
    template_name = 'manager/profile_update.html'
    form_class = UserUpdateForm
    success_url = reverse_lazy('manager:home')
    success_message = _("Your personal information has been updated")

    def get_object(self):
        return self.request.user


class PanelAccessMixin(SingleObjectMixin):
    panel = None

    def post(self, request, *args, **kwargs):
        self.panel = self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.panel = self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return self.request.user.panel_set.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = self.panel
        return context


class PanelRelatedList(SingleObjectMixin, ListView):
    """ Base class to display a list entities related to a panel.

    Specialized to display member and distribution list.
    Ensures that a manager can only view lists related to the panels he manages.
    Subclasses must specify a template_name, and override get_queryset() to
    return the queryset of panel-related entities to display.

    See topics/class-based-views/mixins/#using-singleobjectmixin-with-listview
    in Django documentation for combined usage of SingleObjectMixin with
    ListView.
    """

    def get(self, request, *args, **kwargs):
        self.object = self.panel = self.get_object(queryset=request.user.panel_set.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        """ Return the queryset of panely related entities to display as a list.
        """
        raise NotImplementedError


# Entry point
class Home(RedirectView):
    pattern_name = 'manager:panel-list'


# Panels
class PanelList(ListView):
    template_name = 'manager/panel_list.html'

    def get_queryset(self):
        return self.request.user.panel_set.all()


class PanelDetail(PanelAccessMixin, DetailView):
    model = Panel
    template_name = 'manager/panel_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'panelist_count': Profile.objects.filter(panel=self.object).count(),
            'survey_count': 0,
        })
        return context


class PanelUpdate(SuccessMessageMixin, PanelAccessMixin, UpdateView):
    form_class = PanelUpdateForm
    model = Panel
    template_name = 'manager/panel_update.html'
    success_message = _("Updated panel level variables")

    def get_success_url(self):
        """Redirect to panel detail view"""
        return reverse('manager:panel-detail', args=(self.panel.pk,))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        old_lng = translation.get_language()
        lng = self.request.GET.get('lng', 'en-gb')
        translation.activate(lng)
        contact_info = self.panel.contact_info
        render = render_to_string('panelist/help_text.html', {'INSTANCE_NAME': get_instance_name(lng_to_country(lng)),
                                                              'manager': self.panel.managers.first(),
                                                              'incentive_amount': self.panel.incentive_amount,
                                                              'contact_info': contact_info})
        translation.activate(old_lng) if old_lng else translation.deactivate()
        context['translated_preview'] = render

        return context


# Panel members
class MemberList(FilterView, PanelRelatedList):
    """ List panel members

    See topics/class-based-views/mixins/#using-singleobjectmixin-with-listview
    in Django documentation for combined usage of SingleObjectMixin with
    ListView.
    """
    template_name = 'manager/panel_member_list.html'
    paginate_by = 25
    filterset_class = PanelMemberFilter

    def get_queryset(self):
        return self.object.profile_set.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['counts'] = get_panelist_counts(self.object_list, grand_total_filters={'panel_id': self.panel})
        context["language_codes"] = self.object_list.values_list("language", flat=True).order_by("language").distinct()

        return context


class ProfileCreate(SuccessMessageMixin, PanelAccessMixin, CreateView):
    """

    Cannot inherit from PanelAccessMixin since CreateView also inherits from
    SingleObjectMixin. However, CreateView does not use SingleObjectMixin.get_object(),
    so it is used in this class to retrieve current panel.
    """
    template_name = 'manager/panel_member_create.html'
    form_class = ProfileForm
    success_message = _("Created panelist %(first_name)s %(last_name)s")

    def get_success_url(self):
        """Redirect to panel detail view"""
        return reverse('manager:panel-member-list', args=[self.panel.pk])

    def get_initial(self):
        return {'panel': self.panel.pk}


class ProfileUpdate(SuccessMessageMixin, UpdateView):
    form_class = ProfileForm
    template_name = 'manager/panel_member_update.html'
    success_message = _("Updated panelist %(first_name)s %(last_name)s")

    def get_queryset(self):
        return Profile.objects.filter(
            panel__in=self.request.user.panel_set.all()
        ).select_related('panel')

    def get_success_url(self):
        return reverse('manager:panel-member-list', args=(self.object.panel_id,))


class ProfileDelete(DeleteView):
    """ Delete panel member """
    success_message = _("Deleted panelist %(first_name)s %(last_name)s")
    template_name = "manager/panel_member_confirm_delete.html"

    def get_queryset(self):
        return Profile.objects.filter(
            panel__in=self.request.user.panel_set.all()
        )

    def get_success_url(self):
        return reverse('manager:panel-member-list', args=[self.object.panel_id])

    # TODO How to handle profile deletion ?
    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        # Cannot use SuccessMessageMixin as form_valid is not implemented in BaseDeleteView.
        # https://stackoverflow.com/a/25325228/9208491
        messages.success(
            self.request,
            self.success_message % {'first_name': self.object.first_name, 'last_name': self.object.last_name}
        )
        return response


class ProfileDeactivate(DetailView):
    """ Deactivat panel member """
    success_message = _("Deactivated panelist %(panelist_id)s")
    template_name = "manager/panel_member_confirm_deactivate.html"

    def get_queryset(self):
        return Profile.objects.filter(
            panel__in=self.request.user.panel_set.all()
        )

    def post(self, request, *args, **kwargs):
        profile = self.get_object()
        profile.deactivate()
        messages.success(
            self.request,
            self.success_message % {'panelist_id': profile.panelist_id}
        )
        success_url = reverse('manager:panel-member-update', args=[profile.pk])
        return HttpResponseRedirect(success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['anonymized_values'] = self.object.anonymized_values
        return context


class ProfilePasswordReset(PasswordReset):
    panelist_id = None

    # Raise 404 instead of showing the form if we go on the URL
    def get(self, request, *args, **kwargs):
        raise Http404

    def form_invalid(self, form):
        raise Http404

    def post(self, request, *args, **kwargs):
        self.panelist_id = kwargs.get('pk')
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('manager:panel-member-update', args=(self.panelist_id,))


class ProfileImportCsv(PanelAccessMixin, FormView):
    template_name = 'manager/panel_member_import.html'
    task_id = None
    form_class = CSVImportForm

    def get_success_url(self):
        return reverse('manager:task-import-detail', args=(self.panel.pk, self.task_id))

    def form_valid(self, form):
        dataset = form.cleaned_data["dataset"]
        results = import_data_celery(dataset.headers,
                                     list(dataset),
                                     self.panel.pk,
                                     form.files["dataset"].name,
                                     form.cleaned_data.get('dry_run', True))

        self.task_id = results.id

        return super().form_valid(form)


class TaskImportList(PanelRelatedList):
    template_name = 'manager/task_import_list.html'
    model = GroupTaskImport
    paginate_by = 25

    def get_queryset(self):
        qs = self.object.grouptaskimport_set.all()
        sort = '-' if self.request.GET.get('sort') == "desc" or self.request.GET.get('sort') is None else ''
        order_by = self.request.GET.get('order_by', 'upload_date')
        order_args = [f'{sort}{order_by}']
        return qs.order_by(*order_args)


class TaskImportDetail(DetailView):
    template_name = 'manager/task_import_detail.html'
    model = GroupTaskImport
    pk_url_kwarg = 'task_pk'

    def decompose_result(self):
        task_info = get_task_info(self.kwargs['pk'], self.object.id)
        result = task_info['results']
        errors = task_info['errors']
        completed = task_info['completed']
        dry_run = task_info['dry_run']
        return result, errors, completed, dry_run

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = self.object.panel
        context['result'], context['errors'], context['completed'], context['dry_run'] =\
            self.decompose_result()

        return context


# Surveys
class PanelSurveyList(PanelRelatedList):
    template_name = 'manager/panel_survey_list.html'

    def get_queryset(self):
        # query link distributions that contains the current panel
        qs = self.object.distributions.filter(qx_created_date__isnull=False).order_by('-qx_created_date')
        return qs.select_related('survey')


class PanelSurveyDetail(SingleObjectMixin, FilterView):
    template_name = 'manager/panel_survey_detail.html'
    filterset_class = IndividualLinksFilter
    paginated_by = 25
    pk_url_kwarg = 'linkdistribution_pk'
    history = None

    def get(self, request, *args, **kwargs):
        self.panel: Panel = get_object_or_404(request.user.panel_set.all(), pk=kwargs.get('pk'))
        self.object = super().get_object(queryset=self.panel.distributions.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return self.object.links.filter(profile__panel=self.panel).exclude(url='').prefetch_related('profile')

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        skip_cache = 'nocache' in self.request.GET
        self.history = services.get_distribution_history(qx_id=self.object.qx_id, skip_cache=skip_cache)
        kwargs['history'] = self.history
        return kwargs

    def order_object_list(self, object_list):
        order_by = self.request.GET.get('order_by', "full_name")
        sort_by = (self.request.GET.get('sort', 'asc'))
        sort = False if sort_by == 'asc' else True

        if order_by == 'started_at':
            min_date = datetime(MINYEAR, 1, 1)
            sorted_list = sorted(object_list, key=lambda d: d[order_by] or min_date, reverse=sort)
        else:
            try:
                sorted_list = sorted(object_list, key=lambda d: d[order_by], reverse=sort)
            except KeyError:
                raise Http404

        return sorted_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['panel'] = self.panel
        links = context['object_list']
        history_links = services.merge_links_and_history(links, self.history)
        context['object_list'] = self.order_object_list(history_links)
        profile_ids = [x['profile_id'] for x in context['object_list']]
        context['counts'] = get_panelist_counts(Profile.objects.filter(id__in=profile_ids),
                                                grand_total_present=self.get_queryset().count())

        context['records_stats'] = services.history_links_stats(history_links)
        paginator = Paginator(context['object_list'], self.paginated_by)
        page = self.request.GET.get('page')
        context['profiles'] = paginator.get_page(page)

        return context


class LinkDistributionExport(View):

    panel_pk_url_kwarg = 'pk'
    distribution_pk_url_kwarg = 'linkdistribution_pk'
    columns = ['ess_id', 'status', 'started_at']

    def get_links_for_panel(self, dist, panel):
        """Filter distribution links belonging to given panel"""
        return dist.links.filter(profile__panel=panel).prefetch_related('profile')

    def get_history(self, dist):
        skip_cache = 'nocache' in self.request.GET
        return services.get_distribution_history(qx_id=dist.qx_id, skip_cache=skip_cache)

    def render_to_csv_response(self, history_links, filename):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

        writer = csv.DictWriter(response, fieldnames=self.columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(history_links)

        return response

    def get(self, request, *args, **kwargs):
        panel = get_object_or_404(request.user.panel_set.all(), pk=kwargs.get(self.panel_pk_url_kwarg))
        dist = get_object_or_404(panel.distributions.all(), pk=kwargs.get(self.distribution_pk_url_kwarg))

        links = self.get_links_for_panel(dist, panel)
        history = self.get_history(dist)
        history_links = services.merge_links_and_history(links, history)
        return self.render_to_csv_response(history_links, filename=f"{panel.name}-{dist.short_uid}")


class ProfileExportCsv(SingleObjectMixin, View):

    def get_queryset(self):
        return self.request.user.panel_set.all()

    def get(self, request, *args, **kwargs):
        panel = self.get_object()
        resource = ProfileResource(panel_id=panel.pk)
        exclude_readonly = "all" not in request.GET
        dataset = resource.export(exclude_readonly=exclude_readonly)
        response = csv_response(dataset.csv, 'export-' + panel.name)
        return response


class ProfileExportCustomCsv(FormView):
    template_name = 'manager/customize_export.html'
    form_class = SelectExportForm

    def form_valid(self, form):
        selected_fields = [k for k, v in form.cleaned_data.items() if v]
        panel = self.request.user.panel_set.all().get(pk=self.kwargs['pk'])
        dataset = ProfileResource(panel_id=panel.pk).export(fields=selected_fields)
        response = csv_response(dataset.csv, 'export-' + panel.name)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["panel"] = self.request.user.panel_set.all().get(pk=self.kwargs['pk'])
        return context


def members_import_csv_sample(request):
    resource = ProfileResource()
    fieldnames = resource.get_user_visible_headers()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = "attachment; filename=members_import_sample.csv"
    wr = csv.DictWriter(response, fieldnames=fieldnames)
    wr.writeheader()
    return response


class BlankSlotValueImportCsv(BlankSlotImportCsv, PanelAccessMixin):
    template_name = 'manager/panel_blankslot_value_import.html'

    def get_success_url(self):
        return reverse('manager:panel-member-list', args=(self.panel.pk,))

    def get_resource(self):
        return BlankSlotValueResource(panel_id=self.panel.pk)


class BlankSlotValueUpdate(BaseBlankSlotValueUpdate):
    template_name = 'manager/blankslot_value_formset.html'

    def get_success_url(self):
        return reverse('manager:blankslotvalue-list', args=[self.object.pk])

    def get_queryset(self):
        qs = super().get_queryset()
        panels = self.request.user.panel_set.values_list('pk', flat=True)
        return qs.filter(panel__in=panels)


class BlankSlotValueList(BaseBlankSlotValueList):

    template_name = "manager/blankslot_value_list.html"

    def get_object(self, queryset=None):
        panels = self.request.user.panel_set.values_list('pk', flat=True)
        qs = Profile.objects.filter(panel_id__in=panels)
        return super().get_object(queryset=qs)


class MessageDistributionList(distviews.MessageDistributionList):
    template_name = "manager/msgdist/list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        panel = get_object_or_404(Panel, pk=self.kwargs.get('pk'))
        if self.request.user not in panel.managers.all():
            raise Http404("Panel does not exist")
        return qs.filter(link_distribution__panels=panel)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["panel"] = get_object_or_404(Panel, pk=self.kwargs.get('pk'))
        return context


def download_sms_stats(request, panel_pk, msgdist_pk):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="stats_sms.csv"'

    writer = csv.DictWriter(response, fieldnames=["Panelist ID", "Status", "Bounce Reason", "Last status update"])

    writer.writeheader()
    for stat in SMSStats.objects.filter(msgdist_id=msgdist_pk, panelist__panel_id=panel_pk):
        writer.writerow({"Panelist ID": stat.panelist.panelist_id, "Status": stat.smsstatus,
                         "Bounce Reason": stat.bouncereason, "Last status update": stat.datefile})

    return response


class MessageDistributionDetail(SingleObjectMixin, FilterView):
    template_name = "manager/msgdist/detail.html"
    filterset_class = MessageDeliveryReportFilter
    paginated_by = 25
    pk_url_kwarg = 'msgdist_pk'
    ordering = 'profile__ess_id'
    history = None

    def get(self, request, *args, **kwargs):
        self.object = super().get_object(queryset=MessageDistribution.objects.annotate(Count('links')))
        # There are no detailed stats by panel for sms
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        panel = get_object_or_404(Panel, pk=self.kwargs.get('pk'))
        if self.request.user not in panel.managers.all():
            raise Http404("Panel does not exist")

        return self.object.links.filter(profile__panel=panel).\
            select_related('profile__panel').order_by(self.ordering)

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        skip_cache = 'nocache' in self.request.GET
        if self.object.qx_id:
            self.history = services.get_distribution_history(qx_id=self.object.qx_id, skip_cache=skip_cache)
        kwargs['history'] = self.history
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        skip_cache = 'nocache' in self.request.GET
        context["panel"] = get_object_or_404(Panel, pk=self.kwargs.get('pk'))
        profile_ids = [qs.profile.id for qs in context['object_list']]
        context['counts'] = get_panelist_counts(
            Profile.objects.filter(id__in=profile_ids),
            grand_total_present=self.get_queryset().count(),
        )

        if self.object.qx_id:
            context['object_list'] = services.merge_links_and_history(context['object_list'], self.history)
            paginator = Paginator(context['object_list'], self.paginated_by)
            page = self.request.GET.get('page')
            context['profiles'] = paginator.get_page(page)

            if self.object.is_sms:
                statssms = SMSStats.objects.filter(panelist__panel=context["panel"], msgdist=self.object)
                context['detailedstatssms'] = statssms
                stats = services.get_distribution_stats(
                    qx_id=self.object.qx_id,
                    survey_id=settings.QXSMS_SEND_SURVEY,
                    skip_cache=skip_cache,
                    is_sms=True,
                )
            else:
                stats = services.msg_distributions_stats(context['object_list'])

            context['schedule'] = False
            if datetime.now(timezone.utc) < self.object.get_send_date():
                context['schedule'] = True
                context['days'] = (self.object.get_send_date() - datetime.now(timezone.utc)).days

            context['stats'] = stats

        return context
