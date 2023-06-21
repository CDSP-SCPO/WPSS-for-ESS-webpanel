# -- STDLIB
import itertools

# -- DJANGO
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, TemplateView, UpdateView

# -- QXSMS
from distributions import services
from distributions.models import Link
from qxauth.forms import SetEmailForm, SetPhoneForm
from qxauth.tokens import email_token_generator, phone_token_generator

# -- QXSMS (LOCAL)
from .forms import ProfileUpdateForm
from .utils import panelist_merge_links_and_history

User = get_user_model()


class LinkListView(ListView):
    template_name = 'panelist/survey_list.html'
    model = Link
    ordering = '-distribution__qx_created_date'

    def get_queryset(self):
        return super().get_queryset().filter(
               profile=self.request.user.profile,
        ).select_related('distribution__survey')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # order_by ==> https://www.py4u.net/discuss/221896
        contact_ids = self.object_list.values('qx_contact_id').order_by().distinct()

        # merge history list for each contact_id
        all_histories = list(itertools.chain(
            *[services.get_contact_history(qx_id=c['qx_contact_id']) for c in contact_ids]))
        context['object_list'] = panelist_merge_links_and_history(self.object_list, all_histories)
        return context


class Home(LinkListView):
    template_name = 'panelist/index.html'
    paginate_by = 3

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panelist_first_name'] = self.request.user.profile.first_name
        return context


class Help(TemplateView):
    template_name = 'panelist/help.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        panel = self.request.user.profile.panel
        context['incentive_amount'] = panel.incentive_amount
        contact_info = panel.contact_info
        if contact_info:
            context['contact_info'] = contact_info
        else:
            context['manager'] = panel.managers.first()
        return context


class ProfileUpdate(SuccessMessageMixin, UpdateView):
    form_class = ProfileUpdateForm
    template_name = 'panelist/profile_update.html'
    success_message = _("Your personal information has been updated")
    success_url = reverse_lazy('panelist:home')

    def get_object(self, queryset=None):
        return self.request.user.profile


class EmailChangeView(SuccessMessageMixin, PasswordResetView):
    form_class = SetEmailForm
    template_name = 'panelist/email_change.html'
    title = _('Request email change')
    success_message = _("Email sent to %(email)s, with a link to validate the address")
    # Templates used to generate the address confirmation email
    email_template_name = 'panelist/email_change_email.html'
    html_email_template_name = None
    subject_template_name = 'panelist/email_change_subject.txt'
    success_url = reverse_lazy('panelist:home')
    token_generator = email_token_generator

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class PhoneChangeView(SuccessMessageMixin, PasswordResetView):
    form_class = SetPhoneForm
    template_name = 'panelist/phone_change.html'
    title = _('Request phone number change')
    success_message = _("Text message sent to <b>%(new_phone_number)s</b>, with a link to validate the address")

    success_url = reverse_lazy('panelist:home')
    token_generator = phone_token_generator

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class EmailChangeConfirm(TemplateView):
    template_name = 'panelist/email_change_confirm.html'
    title = _('Confirm email change')
    success_url = reverse_lazy('panelist:home')
    success_message = _("Email address updated.")

    def get_user(self, uidb64):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.select_related('profile__panel').get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
            user = None
        return user

    def save_new_email(self, user):
        user.profile.email = user.profile.temp_email
        user.profile.temp_email = None
        user.profile.temp_email_expiry = None
        user.profile.save()

    def get(self, request, *args, **kwargs):
        assert 'uidb64' in kwargs and 'token' in kwargs
        user = self.get_user(kwargs['uidb64'])
        if user is not None and email_token_generator.check_token(user, kwargs['token']):
            self.save_new_email(user)
            messages.success(self.request, self.success_message)
            return HttpResponseRedirect(self.success_url)
        return super().get(request, *args, **kwargs)


class PhoneChangeConfirm(TemplateView):
    template_name = "panelist/phone_change_confirm.html"
    title = _('Confirm phone change')
    success_url = reverse_lazy('panelist:home')
    success_message = _("Phone number updated.")

    def get_user(self, uidb64):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.select_related('profile__panel').get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
            user = None
        return user

    def save_new_phone(self, user):
        user.profile.phone = user.profile.temp_phone
        user.profile.temp_phone = None
        user.profile.temp_phone_expiry = None
        user.profile.save()

    def get(self, request, *args, **kwargs):
        assert 'uidb64' in kwargs and 'token' in kwargs
        user = self.get_user(kwargs['uidb64'])
        if user is not None and phone_token_generator.check_token(user, kwargs['token']):
            self.save_new_phone(user)
            messages.success(self.request, self.success_message)
            return HttpResponseRedirect(self.success_url)
        return super().get(request, *args, **kwargs)
