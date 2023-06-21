# -- STDLIB
from datetime import timedelta

# -- DJANGO
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.template import loader
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _

# -- THIRDPARTY
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberPrefixWidget

# -- QXSMS
from distributions.services import send_single_sms_distribution
from qxsms import settings

User = get_user_model()


class QxsmsAuthForm(AuthenticationForm):
    field_order = ['username', 'password']

    def get_invalid_login_error(self):
        return ValidationError(
            self.error_messages['invalid_login'],
            code='invalid_login',
            params={'username': self.verbose_label},
        )


class QxsmsAuthByEmailForm(QxsmsAuthForm):
    username_key = 'email'
    verbose_label = _('email address')
    username = forms.EmailField(label=_("Email"))


class QxsmsAuthByPhoneForm(QxsmsAuthForm):
    username_key = 'phone'
    verbose_label = _('phone number')
    username = PhoneNumberField(label=_("Phone number"), widget=PhoneNumberPrefixWidget)


class UserUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {'phone': PhoneNumberPrefixWidget()}


class SetEmailForm(PasswordResetForm):
    error_messages = {
        'email_mismatch': _("The two email addresses didn't match."),
        'email_uniq': _("A user with that email address already exists."),
    }

    # Do not inherit parent field
    email = None

    new_email1 = forms.EmailField(
        label=_('New email'),
    )
    new_email2 = forms.EmailField(
        label=_('New email confirmation'),
    )

    field_order = ['new_email1', 'new_email2']

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def get_users(self, email):
        return (self.user,)

    def clean_new_email1(self):
        email1 = self.cleaned_data.get('new_email1')
        if User.objects.filter(email=email1).exists():
            raise forms.ValidationError(
                self.error_messages['email_uniq'],
                code='email_uniq',
            )
        return email1

    def clean_new_email2(self):
        email1 = self.cleaned_data.get('new_email1')
        email2 = self.cleaned_data.get('new_email2')
        if email1 and email2:
            if email1 != email2:
                raise forms.ValidationError(
                    self.error_messages['email_mismatch'],
                    code='email_mismatch',
                )
        return email2

    def save(self, **opts):
        # Add the chosen new email to cleaned_data for use by PasswordResetForm.save()
        email = self.cleaned_data['email'] = self.cleaned_data["new_email1"]
        self.user.profile.temp_email = email
        self.user.profile.temp_email_expiry = timezone.now() + timedelta(settings.PASSWORD_RESET_TIMEOUT_DAYS)
        self.user.profile.save()
        self.user.email = email  # PasswordResetForm.save() rely on this to send, do not save though
        super().save(**opts)
        return self.user


class SetPhoneForm(PasswordResetForm):
    error_messages = {
        'phone_mismatch': _("The two phone numbers didn't match."),
        'phone_uniq': _("A user with this phone number already exists.")
    }

    email = None

    new_phone_number = PhoneNumberField(label=_("New Phone number"), widget=PhoneNumberPrefixWidget)
    confirm_phone_number = PhoneNumberField(label=_("New Phone number confirmation"), widget=PhoneNumberPrefixWidget)

    field_order = ["new_phone_number", "confirm_phone_number"]

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_phone_number(self):
        new_number = self.cleaned_data.get('new_phone_number')
        if User.objects.filter(phone=new_number).exists():
            raise forms.ValidationError(
                self.error_messages['phone_uniq'],
                code='phone_uniq',
            )
        return new_number

    def clean_confirm_phone_number(self):
        new_phone_number = self.cleaned_data.get('new_phone_number')
        confirm = self.cleaned_data.get('confirm_phone_number')

        if new_phone_number and new_phone_number != confirm:
            raise forms.ValidationError(
                self.error_messages['phone_mismatch'],
                code='phone_mismatch',
            )

        return new_phone_number

    def save(self, *args, use_https=False, token_generator=default_token_generator, request=None, **kwargs):
        phone_number = self.cleaned_data['new_phone_number']

        self.user.profile.temp_phone = phone_number
        self.user.profile.temp_phone_expiry = timezone.now() - timedelta(settings.PASSWORD_RESET_TIMEOUT_DAYS)
        self.user.profile.save()
        current_site = get_current_site(request)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = token_generator.make_token(self.user)
        context = {
            'site_name': current_site.name,
            'domain': current_site.domain,
            'uid': uid,
            'user': self.user,
            'token': token,
            'protocol': 'https' if use_https else 'http',
        }
        message = loader.render_to_string('panelist/phone_change_sms.html', context)
        profile = self.user.profile
        profile.phone = phone_number
        profile_json = profile.to_json()
        # We change the extRef to avoid updating an existing contact
        profile_json.update({
            'extRef': f"PC_{profile_json['extRef']}"
        })
        send_single_sms_distribution(
            name="PC",
            contact=profile_json,
            message=message,
        )
        return self.user


class PhonePasswordResetForm(PasswordResetForm):
    email = PhoneNumberField(label=_("Phone number"), widget=PhoneNumberPrefixWidget)

    def get_users(self, value):
        """ Return users that have a matching email or phone """
        active_users = User.objects.filter(
            phone=value,
            profile__isnull=False,
            is_active=True,
        )
        return (u for u in active_users if u.has_usable_password())

    def save(self, *args, email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator, request=None, **kwargs):

        value = self.cleaned_data['email']

        # Send sms
        for user in self.get_users(value):
            current_site = get_current_site(request)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)
            context = {
                'site_name': current_site.name,
                'domain': current_site.domain,
                'uid': uid,
                'user': user,
                'token': token,
                'protocol': 'https' if use_https else 'http',
            }
            message = loader.render_to_string(email_template_name, context)
            profile = user.profile
            send_single_sms_distribution(
                name="PWDR",
                contact=profile.to_json(),
                message=message,
            )
