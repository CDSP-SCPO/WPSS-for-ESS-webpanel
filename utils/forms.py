# -- DJANGO
from django import forms


class ImportSMSstatsForm(forms.Form):
    file_field = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))
    force_save = forms.BooleanField(required=False)


class ImportSMSstatsEmailForm(forms.Form):
    file_field = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))
    emails = forms.CharField(max_length=56)
