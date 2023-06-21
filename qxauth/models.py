# -- DJANGO
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _

# -- THIRDPARTY
from phonenumber_field.modelfields import PhoneNumberField
from phonenumber_field.phonenumber import PhoneNumber


class QxsmsUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        user = self.model(**extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, password, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(password, **extra_fields)

    def create_superuser(self, password, **extra_fields):
        """
        Create and save an admin user with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(password, phone=None, **extra_fields)

    def get_by_natural_key(self, email_or_phone):
        key = 'phone' if isinstance(email_or_phone, PhoneNumber) else 'email'
        return self.get(**{key: email_or_phone})


class EverybodyIsFreeMixin:
    """Dummy methods so that the admin app works."""
    """https://docs.djangoproject.com/en/2.2/topics/auth/customizing/#custom-users-and-django-contrib-admin"""

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True


class User(AbstractBaseUser, EverybodyIsFreeMixin):
    first_name = models.CharField(_('first name'), max_length=256, blank=True)
    last_name = models.CharField(_('last name'), max_length=256, blank=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    email = models.EmailField(
        _('email address'),
        blank=True,
        unique=True,
        null=True,
        error_messages={
            'unique': _("A user with that email address already exists."),
        }
    )
    phone = PhoneNumberField(
        _('phone number'),
        blank=True,
        null=True,
        unique=True,
        error_messages={
            'unique': _("A user with that phone number already exists."),
        }
    )

    # This might be subject to change,
    # https://gitlab.sciences-po.fr/cdspit/qxsms/issues/51
    is_superuser = models.BooleanField(
        _('superuser status'),
        default=False,
        help_text=_(
            'Designates that this user has all permissions without '
            'explicitly assigning them.'
        ),
    )

    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="user_set",
        related_query_name="user",
    )

    objects = QxsmsUserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        swappable = 'AUTH_USER_MODEL'

    def save(self, *args, **kwargs):
        self.email = self.email or None
        self.phone = self.phone or None
        return super().save(*args, **kwargs)

    def clean(self):
        if not self.email and not self.phone:
            raise ValidationError('At least one of phone or email field must be set.')
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)

    def __str__(self):
        return self.get_username()

    def get_username(self):
        """Return the login username for this User."""
        return self.email or str(self.phone)

    def get_tokens(self):
        uid = urlsafe_base64_encode(force_bytes(self.pk))
        token = default_token_generator.make_token(self)
        return [uid, token]

    def create_password_reset_link(self, request):
        path = reverse('password-reset-confirm', args=self.get_tokens())
        return request.build_absolute_uri(path)

    def send_welcome(self, request=None, template_name='qxauth/welcome_nc.html', subject="Message from WPSS"):
        link = self.create_password_reset_link(request)

        context = {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'link': link,
        }
        html_message = render_to_string(template_name, context)
        send_mail(
            subject=subject,
            message=strip_tags(html_message),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.email],
            html_message=html_message,
        )
