# -- DJANGO
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.forms import ModelMultipleChoiceField

# -- THIRDPARTY
from phonenumber_field.widgets import PhoneNumberPrefixWidget

# -- QXSMS
from utils.csvimport import BlankSlotValueResource

# -- QXSMS (LOCAL)
from .models import Panel

User = get_user_model()


class AddRelatedForm(forms.Form):
    owner_attr = None
    model = None
    queryset = None
    label = None

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)

        if self.queryset is None:
            assert self.model is not None, 'Specify either model or queryset.'
            self.queryset = self.model.objects.all()

        if self.owner_attr is None:
            model_name = self.queryset.model.__name__
            self.owner_attr = model_name.lower() + 's'

        excluded = getattr(owner, self.owner_attr).all()

        self.fields[self.owner_attr] = ModelMultipleChoiceField(
            queryset=self.queryset.exclude(pk__in=excluded),
            label=self.label
        )


class PanelCreateForm(forms.ModelForm):

    class Meta:
        fields = ['name', 'managers']
        model = Panel

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['managers'].queryset = User.objects.filter(groups__name=settings.QXSMS_GROUP_MANAGERS)


class PanelUpdateForm(forms.ModelForm):

    class Meta:
        fields = ['name']
        model = Panel


class ManagerCreateForm(forms.ModelForm):
    """A form to create a manager account.

    Displayed fields:
      first_name
      last_name
      email

    The email will be the login identifier of the newly created manager.
    """

    def __init__(self, *args, **kwargs):
        """Make all field required."""
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    def save(self, *args, **kwargs):

        password = User.objects.make_random_password()
        self.instance.set_password(password)
        with transaction.atomic():
            instance = super().save(*args, **kwargs)
            instance.groups.add(Group.objects.get(name=settings.QXSMS_GROUP_MANAGERS))
        return instance

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {'phone': PhoneNumberPrefixWidget()}


class ManagerUpdateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'is_active']
        widgets = {'phone': PhoneNumberPrefixWidget()}


class PanelAddMultipleForm(AddRelatedForm):
    label = 'Add panels'
    model = Panel
    owner_attr = 'panels'


class ManagerAddMultipleForm(AddRelatedForm):
    label = 'Select managers'
    queryset = User.objects.filter(groups__name=settings.QXSMS_GROUP_MANAGERS)
    owner_attr = 'managers'


class CSVImportBlankSlotForm(forms.Form):
    resource = BlankSlotValueResource()
    fields = [f.column_name for f in resource.get_user_visible_fields()]
