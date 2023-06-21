# -- THIRDPARTY
from import_export import resources, widgets
from import_export.fields import Field

# -- QXSMS
from panelist.models import BlankSlot, BlankSlotValue, Profile

FIELD_MAP = {
    'ess_id': 'idno',
    'first_name': 'name',
    'last_name': 'surname',
    'sex': 'sex',
    'email': 'email',
    'phone': 'mobile',
    'address_property_name': 'propertyname',
    'address_number': 'number',
    'address': 'address',
    'address2': 'address2',
    'city': 'city',
    'county': 'county',
    'postcode': 'postcode',
    'country': 'cntry',
    'language': 'lng',
    'internet_use': 'netusoft',
    'education_years': 'eduyrs',
    'day_of_birth': 'dybrn',
    'month_of_birth': 'mthbrn',
    'year_of_birth': 'yrbrn',
    'is_opt_out': 'opto',
    'opt_out_date': 'dopto',
    'opt_out_reason': 'ropto',
    'delete_contact_data': 'delcontactdata',
    'delete_survey_data': 'delsurveydata',
    'out_of_country': 'movcntry',
    'no_incentive': 'noincen',
    'no_letter': 'nolett',
    'no_text': 'notxt',
    'no_email': 'noem',
    'date_of_birth': 'dob',
    'age': 'age',
    'age_group_code': 'agegrp',
    'panelist_id': 'uid',
    'email_not_blank': 'emailpres',
    'phone_not_blank': 'mobilepres',
    'address_not_blank': 'addresspres',
    'anonymized_since': 'anonsince',
    'false_email': 'falseemail',
    'panel__name': 'panel',
}


class IsNotBlankField(resources.Field):
    """Field that exports 1 if the attribute is not blank, 0 otherwise

    Used for export columns that check for the presence of certain profile attributes,
    without displaying the actual value. Ex: "emailpres" export column that indicates
    whether the profile has an email address provided.

    This logic cannot be handled by a widget, since `import_export.fields.Field` exports
    `None` as empty strings without even bothering to call its widget `.render()` method.
    """
    BLANK_VALUES = [None, ""]

    def export(self, obj):
        value = self.get_value(obj)
        if value in self.BLANK_VALUES:
            return "0"
        return "1"


class EmptyToNoneWidget(widgets.Widget):
    """This widget that transforms an empty string into None is useful for phone and email fields
     so that an empty string is not considered as a new value for the field
    """

    def clean(self, value, row=None, *args, **kwargs):
        if value == '':
            return None
        else:
            return value


class UpperCaseWidget(widgets.Widget):
    """On import if value is an empty string return None to not update data"""

    def clean(self, value, row=None, *args, **kwargs):
        if value is not None:
            value = value.strip().upper()
        return value


class BaseProfileResource(resources.ModelResource):
    """Logic and fields shared between NC and HQ import/export resources"""

    # Read-only properties
    age = Field(readonly=True)
    age_group_code = Field(readonly=True)
    email_not_blank = IsNotBlankField(attribute="email", readonly=True)
    phone_not_blank = IsNotBlankField(attribute="phone", readonly=True)
    address_not_blank = IsNotBlankField(attribute="address", readonly=True)
    anonymized_since = Field(readonly=True)
    false_email = Field(readonly=True)
    panel__name = Field(readonly=True)

    # Model fields requiring special widgets
    language = Field(widget=UpperCaseWidget(), readonly=False)
    country = Field(widget=UpperCaseWidget(), readonly=False)

    def __init__(self, *args, **kwargs):
        """Sets field attribute and column names.

        The convention is to name resource fields as the attribute they represent, and use
        `FIELD_MAP` to derive the corresponding column name.
        """
        super().__init__(*args, **kwargs)
        for (name, field) in self.fields.items():
            field.attribute = field.attribute or name
            field.column_name = FIELD_MAP.get(name, name)

    def dehydrate_false_email(self, profile):
        return "1" if profile.email and profile.email.endswith("opinionsurvey.org") else "0"

    def dehydrate_age(self, profile):
        age = profile.age
        return str(age) if age is not None else "999"

    def dehydrate_date_of_birth(self, profile):
        return f"{profile.day_of_birth or 0:02d}{profile.month_of_birth or 0:02d}{profile.year_of_birth or 0:d}"

    def get_export_order(self):
        """Ensure fields are ordered as in the FIELD_MAP"""
        return tuple(name for name in FIELD_MAP if name in self.fields)


class ProfileResource(BaseProfileResource):
    """Resource used for import and export of profile data by national coordinators."""

    # Read-only properties
    panelist_id = Field(readonly=True)

    # Model fields requiring special widgets
    email = Field(widget=EmptyToNoneWidget(), readonly=False)
    phone = Field(widget=EmptyToNoneWidget(), readonly=False)

    export_fields = None
    exclude_readonly = False

    date_of_birth = Field(readonly=True)

    class Meta:
        model = Profile
        import_id_fields = ('ess_id',)
        skip_unchanged = True
        use_transactions = True
        clean_model_instances = True
        fields = ('ess_id', 'first_name', 'last_name', 'sex', 'email', 'phone', 'address_property_name',
                  'address_number', 'address', 'address2', 'city', 'county', 'postcode', 'country',
                  'internet_use', 'education_years', 'day_of_birth', 'month_of_birth', 'year_of_birth', 'is_opt_out',
                  'opt_out_date', 'opt_out_reason', 'delete_contact_data', 'delete_survey_data', 'out_of_country',
                  'no_incentive', 'no_letter', 'no_text', 'no_email', 'age')
        widgets = {
            'opt_out_date': {'format': '%d%m%Y'},
        }

    def __init__(self, *args, panel_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.panel_id = panel_id

    def get_import_fields(self):
        """All editable fields

        Used by Resource.skip_row() and Resource.import_obj()
        """
        return [f for f in self.get_fields() if not f.readonly]

    def get_export_fields(self):
        """Select the fields to export based on the `export_fields` and `exclude_readonly`  attributes.

                If `export_fields` is set, it is a list indicating the fieldnames to export.
                If `export_fields` is not set, and `exclude_readonly` is `True`, export only editable fields.
                Otherwise, export all fields.
        """
        if self.export_fields is not None:
            # Preserve the FIELD_MAP ordering of fields when restricting
            export_fields = [name for name in FIELD_MAP if name in self.export_fields]
            return [self.fields[name] for name in export_fields if name in self.fields]
        if self.exclude_readonly:
            return self.get_import_fields()
        return self.get_fields()

    def get_user_visible_fields(self):
        """All editable fields

        Used by Diff class to compare saved instance to the original.
        """
        return self.get_import_fields()

    def before_export(self, queryset=None, *args, fields=None, exclude_readonly=False, **kwargs):
        self.export_fields = fields
        self.exclude_readonly = exclude_readonly

    def get_queryset(self):
        return super().get_queryset().filter(panel_id=self.panel_id)

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        """As a convenience, allow attribute names as headers"""
        headers = dataset.headers
        dataset.headers = [FIELD_MAP.get(name, name) for name in headers]

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        """Set related panel on the instance"""
        if instance.panel_id is None:
            instance.panel_id = self.panel_id


class ProfileForeignKeyWidget(widgets.ForeignKeyWidget):

    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.filter(country=row["cntry"])


class ProfileHQResource(BaseProfileResource):

    class Meta:
        model = Profile
        fields = (
            'ess_id',
            'country',
            'sex',
            'education_years',
            'internet_use',
            'is_opt_out',
            'opt_out_date',
            'opt_out_reason',
            'delete_contact_data',
            'delete_survey_data',
            'out_of_country',
            'no_incentive',
            'no_letter',
            'no_text',
            'no_email'
        )
        widgets = {
            'opt_out_date': {'format': '%d%m%Y'},
        }


class BlankSlotValueResource(resources.ModelResource):

    profile = resources.Field(
        attribute="profile",
        column_name="idno",
        widget=ProfileForeignKeyWidget(Profile, field="ess_id")
    )

    blankslot = resources.Field(
        attribute="blankslot",
        column_name="addvar",
        widget=widgets.ForeignKeyWidget(BlankSlot, field="name")
    )

    country = resources.Field(
        attribute='profile__country',
        column_name='cntry',
        readonly=True
    )

    class Meta:
        model = BlankSlotValue
        fields = ('value',)
        import_id_fields = ('profile', 'blankslot')
        export_order = ('country', 'profile', 'blankslot', 'value')
        skip_unchanged = True
        use_transactions = True

    def __init__(self, *args, panel_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.panel_id = panel_id

    def before_save_instance(self, instance, using_transactions, dry_run):
        """Check that we are allowed to alter blank slot values for this panelist."""
        if self.panel_id and instance.profile.panel.pk != self.panel_id:
            raise ValueError('Attempted modifications outside of current panel.')

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.panel_id is not None:
            queryset = queryset.filter(profile__panel_id=self.panel_id)
        return queryset
