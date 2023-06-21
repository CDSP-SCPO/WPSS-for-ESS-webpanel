# -- STDLIB
import codecs
import csv
import io
import uuid
from datetime import datetime

# -- DJANGO
from django.conf import settings
from django.core.mail import EmailMessage
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, ListView
from django.views.generic.detail import (
    SingleObjectMixin, TemplateResponseMixin,
)
from django.views.generic.edit import ProcessFormView

# -- QXSMS
from distributions.models import MessageDistribution
from hq.models import Panel, SMSStats
from panelist.forms import BlankSlotValueFormSet
from panelist.models import Profile
from utils.csvimport import BlankSlotValueResource
from utils.forms import ImportSMSstatsEmailForm, ImportSMSstatsForm


def csv_response(dataset, file_name='export'):
    response = HttpResponse(dataset, content_type='text/csv')
    filename = f"{timezone.now().strftime('%Y-%m-%d-%H%M')}-{file_name}.csv"
    response['Content-Disposition'] = f"attachment; filename={filename}"
    return response


def blank_slot_export_csv(request, panel_pk=None):
    if panel_pk is not None:
        try:
            panel = request.user.panel_set.all().get(pk=panel_pk)
            dataset = BlankSlotValueResource(panel_id=panel.id).export()
        except Panel.DoesNotExist:
            raise Http404
    else:
        dataset = BlankSlotValueResource().export()

    response = csv_response(dataset.csv, 'export-panel-blank-slots')
    return response


class BaseBlankSlotValueUpdate(SingleObjectMixin, TemplateResponseMixin, ProcessFormView):
    """Base class to edit the set of blank slot values related to a profile.

    Subclasses must specify a template name and implement `BaseBlankSlotValueUpdate.get_success_url()`
    """

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        raise NotImplementedError

    def get_queryset(self):
        return Profile.objects.all()

    def get_form(self):
        kwargs = {
            'profile_id': self.object.pk,
        }
        if self.request.method in ('POST', 'PUT'):
            kwargs['data'] = self.request.POST

        return BlankSlotValueFormSet(**kwargs)

    def form_valid(self, formset):
        """Save blank slot values and update Qualtrics contact embedded data"""
        formset.save()
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, formset):
        return self.render_to_response(self.get_context_data(formset=formset))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'formset' not in context:
            context['formset'] = self.get_form()
        context['panel'] = self.object.panel
        context['profile'] = self.object
        return context


class BaseBlankSlotValueList(SingleObjectMixin, ListView):
    """List blank slot values related to a profile"""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = Profile.objects.all()
        return super().get_object(queryset=queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.object
        context['panel'] = self.object.panel
        return context

    def get_queryset(self):
        return self.object.blankslotvalue_set.all()


class ImportSMSStats(FormView):
    form_class = ImportSMSstatsForm
    template_name = "utils/import_sms_stats.html"
    template_name_success = "utils/import_sms_stats_result.html"
    success_url = reverse_lazy("utils:import-sms-stats")

    def form_valid(self, form):
        files = self.request.FILES.getlist("file_field")
        allprofiles, datain, import_stats = self.file_analysys(files)
        for d in datain:
            import_stats[d["filename"]]["total"] += 1
            try:
                p = allprofiles[uuid.UUID(d["External Data Reference"])]
            except KeyError:
                import_stats[d["filename"]]["errors"].append(d["External Data Reference"])
                continue

            stats, x = SMSStats.objects.get_or_create(panelist=p, msgdist=d["msgdist"])

            stats.smsstatus = d["Status"]
            stats.bouncereason = d["Bounce Reason"]
            if form.cleaned_data["force_save"] or not stats.datefile or stats.datefile <= d["filedate"]:
                import_stats[d["filename"]]["save"] += 1
                stats.datefile = d["filedate"]
                stats.save()
        return render(self.request, self.template_name_success,
                      context={"import_stats": import_stats.items()})

    def get_filedate(self, data):
        filedate, x = data.split(".")
        filedate = datetime.strptime(filedate, "%Y-%m-%dT%H-%M-%SZ").replace(tzinfo=timezone.utc)
        return filedate

    def file_analysys(self, files):
        datain = []
        alluids = []
        import_stats = dict()

        for f in files:
            reader = csv.DictReader(codecs.iterdecode(f, 'utf-8'))
            filetype, data = f.name.split("-", 1)
            if "Distribution_history" in filetype:  # Distribution_history-DATE.csv
                filedate = self.get_filedate(data)
                import_stats[f.name] = {"errors": [], "save": 0, "total": 0}
                for r in reader:
                    try:
                        msgdist = MessageDistribution.objects.get(qx_id=r["Distribution Id"])
                    except MessageDistribution.DoesNotExist:
                        import_stats[f.name]["errors"].append(
                                f"MessageDistribution with qx_id '{r['Distribution Id']}' not found"
                            )
                        import_stats[f.name]["total"] += 1
                        continue
                    r["filename"], r["msgdist"], r["filedate"] = f.name, msgdist, filedate
                    alluids.append(r["External Data Reference"])
                    datain.append(r)
            elif "export" in filetype:  # export-MSGDISTQXID-DATE.csv
                msgdist_qx_id, filedate = data.split("-", 1)
                filedate = self.get_filedate(filedate)

                try:
                    msgdist = MessageDistribution.objects.get(qx_id=msgdist_qx_id)
                    import_stats[f.name] = {"errors": [], "save": 0, "total": 0}
                except MessageDistribution.DoesNotExist:
                    import_stats[f.name] = f"MessageDistribution with qx_id '{msgdist_qx_id}' not found"
                    continue
                for r in reader:
                    r["filename"], r["msgdist"], r["filedate"] = f.name, msgdist, filedate
                    alluids.append(r["External Data Reference"])
                    datain.append(r)
            else:  # error
                import_stats[f.name] = "Unknown filename format"

        allprofiles = {p.uid: p for p in Profile.objects.filter(uid__in=alluids)}

        return allprofiles, datain, import_stats


class ImportSMSStatsEmail(FormView):
    form_class = ImportSMSstatsEmailForm
    template_name = "utils/import_sms_stats.html"
    success_url = reverse_lazy("utils:email-sms-stats")

    def form_valid(self, form):
        datain = []
        dataout = []
        uidnotfound = []
        alluids = []
        files = self.request.FILES.getlist("file_field")

        for f in files:
            reader = csv.DictReader(codecs.iterdecode(f, 'utf-8'))
            for r in reader:
                r["filename"] = f.name
                alluids.append(r["External Data Reference"])
                datain.append(r)

        allprofiles = {p.uid: p for p in Profile.objects.filter(uid__in=alluids)}

        for d in datain:
            try:
                p = allprofiles[uuid.UUID(d["External Data Reference"])]
            except KeyError:
                uidnotfound.append(d["External Data Reference"])
                continue
            dataout.append({"filename": d["filename"],
                            "country": p.country,
                            "essid": p.ess_id,
                            "panelname": p.panel.name,
                            "SMSstatus": d["Status"],
                            "BounceReason": d["Bounce Reason"]})

        with io.StringIO() as fd:
            w = csv.DictWriter(fd, fieldnames=["filename", "country", "essid", "panelname", "SMSstatus",
                                               "BounceReason"])
            w.writeheader()
            w.writerows(dataout)
            outvalue = fd.getvalue()

        email = EmailMessage("SMS Stats", f"SMS Stats for {'&'.join([f.name for f in files])}\n\n"
                                          f"UID not found : {uidnotfound}",
                             settings.DEFAULT_FROM_EMAIL, form.cleaned_data["emails"].split(";"))
        email.attach("sms-stats.csv", outvalue)
        email.send()

        return super().form_valid(form)
