# -- DJANGO
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView, PasswordChangeView, PasswordResetConfirmView, PasswordResetView,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

# -- QXSMS
from qxauth.forms import (
    PhonePasswordResetForm, QxsmsAuthByEmailForm, QxsmsAuthByPhoneForm,
)


class AppLabelMixin:
    group_app_labels = {
        settings.QXSMS_GROUP_ADMINS: 'hq',
        settings.QXSMS_GROUP_MANAGERS: 'manager',
        settings.QXSMS_GROUP_PANEL_MEMBERS: 'panelist'
    }

    def get_user_app_label(self):
        user_group = self.request.user.groups.values_list('name', flat=True).first()
        try:
            if self.request.user.is_superuser and user_group not in self.group_app_labels:
                return 'admin'
            return self.group_app_labels[user_group]
        except KeyError:
            if not self.request.user.is_anonymous:
                raise PermissionDenied

    def get_success_url(self):
        label = self.get_user_app_label()
        if label == 'admin':
            return reverse('admin:index')
        return reverse(f'{label}:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_label'] = self.get_user_app_label()
        return context


class GroupLogin(AppLabelMixin, LoginView):
    """Login view that redirects based on group membership."""
    redirect_authenticated_user = True
    template_name = 'login.html'
    login_method = 'email'

    def dispatch(self, request, *args, **kwargs):
        if 'phone' in self.request.GET:
            self.login_method = 'phone'
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.get_redirect_url() or super().get_success_url()

    def get_form_class(self):
        if self.login_method == 'phone':
            return QxsmsAuthByPhoneForm
        return QxsmsAuthByEmailForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['login_method'] = self.login_method
        return context


class PasswordChange(LoginRequiredMixin, AppLabelMixin, PasswordChangeView):
    def get_template_names(self):
        app_label = self.get_user_app_label()
        return [f"{app_label}/password_change.html"]


class PasswordReset(SuccessMessageMixin, PasswordResetView):
    form_class = PasswordResetForm
    template_name = 'password_reset.html'
    email_template_name = 'password_reset_email.html'
    success_message = _("An email with a password reset link has been sent.")
    success_url = reverse_lazy('login')
    extra_context = {'reset_method': 'email'}

    def dispatch(self, request, *args, **kwargs):
        if 'phone' in self.request.GET:
            self.form_class = PhonePasswordResetForm
            self.success_message = _("An sms with a password reset link has been sent.")
            self.extra_context = {'reset_method': 'phone'}

        return super().dispatch(request, *args, **kwargs)


class PasswordResetConfirm(SuccessMessageMixin, PasswordResetConfirmView):
    template_name = 'password_reset_confirm.html'
    success_message = _("Password updated!")
    success_url = reverse_lazy('login')
    post_reset_login = True
