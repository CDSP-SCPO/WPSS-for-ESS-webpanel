# -- STDLIB
from typing import Iterable, Optional

# -- DJANGO
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# -- QXSMS (LOCAL)
from .models import LinkDistribution, Message, MessageDistribution, Survey


def _filter_surveys(surveys):
    return [s for s in surveys if s['id'] != settings.QXSMS_SEND_SURVEY
            and s['isActive'] is True]


class LinkDistributionForm(forms.ModelForm):
    survey = forms.ChoiceField(choices=(),
                               help_text="Eligible surveys are those that are active and"
                               " shared with the WPSS Qualtrics user.")

    class Meta:
        model = LinkDistribution
        fields = ('panels', 'description')
        help_texts = {
            'panels': 'Hold down the SHIFT key while clicking to select several panels',
            'description': 'A concise way to unambiguously refer to this link set',
        }

    def __init__(self, surveys, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.surveys = {s['id']: s['name'] for s in _filter_surveys(surveys)}
        self.fields['survey'].choices = self.surveys.items()

    def save(self, commit=True):
        self.instance.survey = self.get_survey_instance()
        return super().save(commit=commit)

    def get_survey_instance(self):
        qx_id = self.cleaned_data['survey']
        name = self.surveys[qx_id]
        survey, created = Survey.objects.update_or_create(pk=qx_id, defaults={'name': name})
        return survey


class LinkDistributionGenerateForm(forms.ModelForm):

    class Meta:
        model = LinkDistribution
        fields = ('expiration_date',)
        help_texts = {
            'expiration_date': "YYYY-MM-DD",
        }

    def clean(self):
        """
        Checks that the Panel doesn't have empty contacts list
        """
        if not self.instance.count_candidates:
            raise ValidationError(_("All panels are empty, there are no links to generate."))
        return super().clean()


# -- Message distributions
class QxMessageField(forms.ChoiceField):

    def __init__(self, *args, messages: Iterable[dict] = (), **kwargs):
        # We don't need to call ChoiceField.__init__() since choices
        # will be initialized when we set the 'messages' property.
        forms.Field.__init__(self, *args, **kwargs)
        self.messages = messages

    def _set_messages(self, messages: Iterable[dict]) -> None:
        self._messages = {message['id']: message for message in messages}
        self.choices = [(message['id'], message['description']) for message in messages]

    def _get_messages(self):
        return self._messages

    messages = property(_get_messages, _set_messages)

    def clean(self, value):
        value = super().clean(value)
        message = self._messages[value]
        return _build_message_instance(message)


def _build_message_instance(message):
    return Message(
        qx_id=message['id'],
        description=message['description'],
        category=message['category']
    )


def _message_choices(messages: Iterable[dict]) -> Iterable[tuple[str, str]]:
    return [(message['id'], message['description']) for message in messages]


class BaseMessageDistributionForm(forms.ModelForm):
    contact_mode = None

    message = QxMessageField(help_text=_("From Qualtrics library"))
    subject = QxMessageField(help_text=_("From Qualtrics library"))

    class Meta:
        model = MessageDistribution
        fields = ('link_distribution', 'target', 'description')

    def __init__(self, *args, messages: list[dict],
                 subjects: Optional[list[dict]] = None,
                 description: Optional[str] = None,
                 **kwargs):

        super().__init__(*args, **kwargs)
        subjects = subjects or []
        self.fields['message'].messages = messages
        self.fields['description'].messages = description
        if 'subject' in self.fields and subjects is not None:
            self.fields['subject'].messages = subjects

    def save(self, commit=True):
        self.instance.contact_mode = self.contact_mode
        for field in ('message', 'subject'):
            message_instance = self.cleaned_data.get(field)
            if message_instance is None:
                continue
            if commit:
                message_instance.save()
            setattr(self.instance, field, message_instance)
        return super().save(commit=commit)


class EmailDistributionForm(BaseMessageDistributionForm):

    contact_mode = MessageDistribution.MODE_EMAIL

    class Meta(BaseMessageDistributionForm.Meta):
        labels = {
            'link_distribution': _('Link set'),
            'message': _("Email message"),
            'subject': _("Email subject")
        }


class SMSDistributionForm(BaseMessageDistributionForm):

    contact_mode = MessageDistribution.MODE_SMS
    subject = None

    class Meta(BaseMessageDistributionForm.Meta):
        labels = {
            'link_distribution': _('Link set'),
            'message': _("SMS message")
        }


class QxMessageForm(forms.Form):

    message = QxMessageField(help_text=_("From Qualtrics library"))
    subject = QxMessageField(help_text=_("From Qualtrics library"))

    def __init__(self, *args, messages, subjects=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['message'].messages = messages
        if subjects is not None:
            self.fields['subject'].messages = subjects
        else:
            self.fields.pop('subject')

    def save(self, commit=True):
        message = self.cleaned_data.get('message')
        subject = self.cleaned_data.get('subject')
        if commit:
            message.save()
            subject is not None and subject.save()
        return message, subject


class MessageDistributionSendForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        """
        Pass Link distribution history, to validate the form
        """

        self.history = kwargs.pop('history')
        super().__init__(*args, **kwargs)

    class Meta:
        model = MessageDistribution
        fields = ('send_date',)

    def clean(self):
        """
        Checks that the Panel doesn't have empty contacts list
        i we have fallback we will check if it's not empty
        """
        cleaned_data = super().clean()
        stats = self.instance.get_candidates_stats(self.history)
        # Freeze the set of recipients
        if not stats['contact_mode']:
            raise ValidationError(_("The Panel must have at least one eligible contact"))

        if self.instance.has_fallback and not stats['fallback_mode']:
            raise ValidationError(_("The Panel must have at least one eligible contact with fallback"))

        return cleaned_data


class MessageDistributionDescriptionUpdateForm(BaseMessageDistributionForm):

    class Meta:
        model = MessageDistribution
        fields = ('description',)
