# -- DJANGO
from django.forms import (
    BaseModelFormSet, HiddenInput, ModelChoiceField, ModelForm,
    ValidationError, modelformset_factory,
)
from django.utils.translation import gettext_lazy as _

# -- THIRDPARTY
from phonenumber_field.widgets import PhoneNumberPrefixWidget

# -- QXSMS (LOCAL)
from .models import BlankSlot, BlankSlotValue, Panel, Profile


class ProfileForm(ModelForm):
    """Create a profile, or update an existing one.

    Includes 'panel' as a hidden disabled field, so that uniqueness
    of the pair (ess_id, panel) is checked. The initial value of this field must
    be provided through `initial` if no instance is bound to the form.
    """

    # Fields we want to be able to edit even after the panelist deactivation.
    ALLOWED_FIELDS_WHEN_DEACTIVATED = ['opt_out_date', 'opt_out_reason', 'delete_survey_data']

    panel = ModelChoiceField(queryset=Panel.objects.all(), widget=HiddenInput, disabled=True)

    class Meta:
        model = Profile
        fields = [
            'panel',
            'ess_id',
            'first_name',
            'last_name',
            'sex',
            'email',
            'phone',
            'address_property_name',
            'address_number',
            'address',
            'address2',
            'city',
            'county',
            'postcode',
            'country',
            'language',
            'internet_use',
            'education_years',
            'day_of_birth',
            'month_of_birth',
            'year_of_birth',
            'is_opt_out',
            'opt_out_date',
            'opt_out_reason',
            'delete_contact_data',
            'delete_survey_data',
            'out_of_country',
            'no_incentive',
            'no_letter',
            'no_text',
            'no_email',
        ]

        help_texts = {
            'is_opt_out':
                "If checked, individual links will no longer be generated for this panelist and\
                no messages will be sent to them.<br>\
                Unchecking it will allow the panelist to participate to next surveys, \
                when new individual links will be generated.",
            'language':
                "Please visit <a href='https://api.qualtrics.com/guides/docs/Instructions/language-codes.md'>\
                Qualtrics' documentation</a> for a list of natively supported language codes.",
            'opt_out_date': "YYYY-MM-DD",
            'delete_contact_data': "Automatically checked when the panelist is deactivated and anonymized.",
            'delete_survey_data': "The survey data needs to be deleted. Only used to store the information, \
                does not trigger any automated action.",
            'no_text': "If checked, the panelist will not receive text messages. The survey link will still be \
                accessible via the panelist portal or email (if \"No email\" is not checked).",
            'no_email': "If checked, the panelist will not receive emails. The survey link will still be \
                accessible via the panelist portal or text message (if \"No text\" is not checked).",
        }

        widgets = {
            'phone': PhoneNumberPrefixWidget()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The deactivation process takes care of this field.
        self.fields['delete_contact_data'].disabled = True

        # If user is deactivated.
        if self.instance.user and not self.instance.is_active:
            self.fields['language'].required = False  # Remove validation when deactivated.
            for key, field in self.fields.items():
                if key in self.ALLOWED_FIELDS_WHEN_DEACTIVATED:
                    continue  # Skip this field.
                field.disabled = True
        elif self.initial.get('ess_id'):
            self.fields['ess_id'].disabled = True

        email = self.initial.get('email')
        if email and email.endswith("opinionsurvey.org"):
            self.fields['email'].help_text = "<div class='form-check'>\
            <input type='checkbox' name='false_email' \
            class='form-check-input' disabled id='id_false_email' checked>\
            <label class='form-check-label' for='id_false_email'>False email</label></div>"


# Profile update by panelists
class ProfileUpdateForm(ModelForm):
    class Meta:
        model = Profile
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'address_property_name',
            'address_number',
            'address',
            'address2',
            'city',
            'county',
            'postcode',
            'country',
            'language',
            'day_of_birth',
            'month_of_birth',
            'year_of_birth',
        ]

        widgets = {'phone': PhoneNumberPrefixWidget()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        to_disable = [
            'email',
            'country',
            'language',
            'day_of_birth',
            'month_of_birth',
            'year_of_birth',
            'phone',
        ]
        for fieldname in to_disable:
            self.fields[fieldname].disabled = True


class BlankSlotValueForm(ModelForm):
    """Edit or create a blank slot value related to a given profile

    Since this form is meant to be used within a formset displaying all blank slot
    values related to a given profile, the blankslot field need not be editable, unless
    a new instance is being created.

    Expects `profile` and `blankslot` to be specified in the `initial` data dict.
    """
    # TODO Probably useless...
    # Could be set in save()
    # profile = ModelChoiceField(
    #     queryset=Profile.objects.all(),
    #     disabled=True,
    #     widget=HiddenInput,
    # )

    class Meta:
        model = BlankSlotValue
        fields = ('blankslot', 'value')
        labels = {'blankslot': '', 'value': ''}

    def __init__(self, *args, blankslot_choices, **kwargs):
        """Set available blankslot choices and disable this field if we are updating."""
        super().__init__(*args, **kwargs)
        f = self.fields['blankslot']
        if self.instance.pk is not None:
            f.disabled = True
        f.choices = blankslot_choices

    def save(self, commit=True):
        if self.instance.pk is None:
            self.instance.profile_id = self.initial.get('profile')
        return super().save(commit=commit)


class BaseBlankSlotValueFormset(BaseModelFormSet):
    """Edit, delete or create blank slot values for a given profile

    - `profile_id` identifies the `Profile` whose blank slot values are being edited

    - `queryset`, if given, determines the blank slot values to edit or delete. By default, consists
    of all values related to `profile_id`.
    """

    def __init__(self, *args, profile_id, queryset=None, **kwargs):
        # The set of blank slot values on which we want to operate.
        if queryset is None:
            queryset = BlankSlotValue.objects.filter(profile_id=profile_id)
        # Compute once the choices shared by ModelChoiceField instances.
        # Otherwise, each `blankslot` field would issue a database query when rendering
        self.blankslot_choices = list(BlankSlot.objects.order_by('name').values_list('pk', 'name'))
        # For creation forms, let the user choose among blankslots not already taken
        taken_slots = queryset.values_list('blankslot_id', flat=True)
        self.free_blankslot_choices = [(pk, name) for (pk, name) in self.blankslot_choices if pk not in taken_slots]
        # The number of extra creation forms to display
        self.extra = min(len(self.free_blankslot_choices), self.extra)
        # Initial data passed to extra creation forms. Set a different free blankslot for each.
        initial = [{'profile': profile_id, 'blankslot': self.free_blankslot_choices[i][0]} for i in range(self.extra)]
        super().__init__(queryset=queryset, initial=initial, *args, **kwargs)

    def get_form_kwargs(self, index):
        """Pass available blankslot choices to each `BlankSlotValueForm`"""
        for_update = index < self.initial_form_count()
        blankslot_choices = self.blankslot_choices if for_update else self.free_blankslot_choices
        return {'blankslot_choices': blankslot_choices}

    def clean(self):
        """Ensure that a blank slot is not being assigned a value twice.

        Because we are not calling `BaseModelFormSet.clean()`, uniqueness checks are bypassed.
        Since we know that all `BlankSlotValue` instances will have the same `profile_id`, it is sufficient
        to check that all assigned blank slots are different. This is more efficient than calling
        `validate_unique()` on each instance.
        """

        bs_objs = [form.cleaned_data.get('blankslot') for form in self.forms]
        bs_pk = [bs.pk for bs in bs_objs if bs is not None]
        if len(bs_pk) != len(set(bs_pk)):
            # Translators: ignore
            raise ValidationError(_("Cannot assign multiple values to the same variable"))


BlankSlotValueFormSet = modelformset_factory(
    BlankSlotValue,
    BlankSlotValueForm,
    formset=BaseBlankSlotValueFormset,
    # Maximum number of extra forms to create new instances
    extra=5,
    can_delete=True
)
