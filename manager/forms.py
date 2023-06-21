# -- STDLIB
import csv

# -- DJANGO
from django import forms
from django.conf import settings
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

# -- THIRDPARTY
import tablib

# -- QXSMS
from hq.models import Panel
from utils.csvimport import FIELD_MAP, BlankSlotValueResource, ProfileResource


class CSVDatasetField(forms.FileField):
    """ Expects a CSV file with specified headers

    Inspired from https://djangosnippets.org/snippets/10596/
    """

    ID_NAME = 'idno'
    MAX_LINES = 1000
    default_error_messages = {
        'invalid_fields': _("Expected CSV fields (or a subset): %(expected_fields)s.\n"
                            "Got the following unexpected fields: %(fields)s."),
        'invalid_file': _("Invalid CSV file."),
        'invalid_encoding': _("UTF8 text encoding is expected."),
        'invalid_file_length': _(f"Invalid file length (should be no more than {MAX_LINES} rows).")
    }

    def __init__(self, *args, expected_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.expected_fields = expected_fields
        self.widget.attrs.update({'accept': '.csv'})

    def to_python(self, data):
        data = super().to_python(data)
        try:
            csv_str = data.read().decode('utf8')
            dataset = tablib.import_set(csv_str, format='csv')
        except UnicodeError:
            raise forms.ValidationError(self.error_messages['invalid_encoding'], code='invalid_encoding')
        except (csv.Error, tablib.InvalidDimensions):
            raise forms.ValidationError(self.error_messages['invalid_file'], code='invalid_file')
        if len(dataset) > self.MAX_LINES:
            raise forms.ValidationError(self.error_messages['invalid_file_length'], code='invalid_file_length')

        dataset.headers = self.clean_header(dataset.headers or [])
        return dataset

    def clean_header(self, headers):
        """Normalize header fields by lowercasing and stripping whitespace"""
        header = [h.lower().strip() for h in headers]
        if self.expected_fields and not set(header).issubset(set(self.expected_fields)):
            expected = ", ".join(self.expected_fields)
            unexpected_fields = ", ".join(set(header).difference(set(self.expected_fields)))
            raise forms.ValidationError(
                self.error_messages['invalid_fields'],
                params={'expected_fields': expected, 'fields': unexpected_fields},
                code='invalid_fields'
            )
        return header


class CSVImportForm(forms.Form):
    resource = ProfileResource()
    fields = resource.get_user_visible_headers()
    dataset = CSVDatasetField(
        label='CSV file',
        required=True,
        expected_fields=fields,
        help_text=_(f"The following header line is expected: {','.join(fields)}")
    )
    dry_run = forms.BooleanField(label=_('Dry run'), required=False,
                                 widget=forms.CheckboxInput if settings.DEBUG else forms.HiddenInput)


class SelectExportForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in FIELD_MAP:
            self.fields[f] = forms.BooleanField(initial=True, required=False)


class BlankSlotImportForm(forms.Form):
    resource = BlankSlotValueResource()
    fields = [f.column_name for f in resource.get_user_visible_fields()]
    dataset = CSVDatasetField(
        label='CSV file',
        required=True,
        expected_fields=fields,
        help_text=f"The following header line is expected: {','.join(fields)}"
    )


class PanelUpdateForm(ModelForm):
    class Meta:
        fields = ['incentive_amount', 'contact_info']
        model = Panel
