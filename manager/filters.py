# -- DJANGO
from django import forms

# -- THIRDPARTY
import django_filters

# -- QXSMS
from distributions.models import has_failed, has_opened, is_success
from panelist.models import Profile


class PanelMemberFilter(django_filters.FilterSet):

    ess_id = django_filters.CharFilter(
        field_name="ess_id",
        label="ESS ID",
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    first_name = django_filters.CharFilter(
        field_name="first_name",
        label="First name",
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = django_filters.CharFilter(
        field_name="last_name",
        label="Last name",
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = django_filters.CharFilter(
        field_name="email",
        label="Email",
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    sex = django_filters.MultipleChoiceFilter(
        choices=Profile.SEXES,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Profile
        fields = ['ess_id', 'email', 'phone', 'first_name', 'last_name', 'sex']

    @property
    def qs(self):
        queryset = super().qs
        order_by = self.request.GET.get('order_by') or 'id'
        sort = self.request.GET.get('sort') or 'asc'
        order = "-" + order_by if sort == "desc" else order_by
        return queryset.all().order_by(order)


class IndividualLinksFilter(django_filters.FilterSet):

    def __init__(self, *args, history, **kwargs):
        self.history = history
        super().__init__(*args, **kwargs)

    STATUS_CHOICES = (
        ("SurveyFinished", "Finished"),
        ("SurveyStarted", "Started"),
        ("SurveyPartiallyFinished", "Partially finished"),
        ("Pending", "Not started"),
    )

    profile = django_filters.NumberFilter(field_name='profile__ess_id', label='ESS ID')
    status = django_filters.ChoiceFilter(choices=STATUS_CHOICES, method='status_filter', label='Status')

    def status_filter(self, queryset, name, value):
        contact_ids = [panelist['contactId'] for panelist in self.history if panelist['status'] == value]
        return queryset.filter(qx_contact_id__in=contact_ids)


class MessageDeliveryReportFilter(django_filters.FilterSet):

    def __init__(self, *args, history, **kwargs):
        self.history = history
        super().__init__(*args, **kwargs)

    OTHER_FAILURES = "Other_Failures"

    STATUS_CHOICES = (
        ("Success", "Success"),
        ("Opened", "Opened"),
        ("HardBounce", "Hard Bounce"),
        ("SoftBounce", "Soft Bounce"),
        (OTHER_FAILURES, "Other Failures"),
    )

    profile = django_filters.NumberFilter(field_name='profile__ess_id', label='ESS ID')
    status = django_filters.ChoiceFilter(choices=STATUS_CHOICES, method='status_filter', label='Status')

    def status_filter(self, queryset, name, value):
        if value == self.OTHER_FAILURES:
            contact_ids = [panelist['contactId'] for panelist in self.history
                           if has_failed(panelist)]

        elif value == 'Success':
            contact_ids = [panelist['contactId'] for panelist in self.history
                           if is_success(panelist) or has_opened(panelist)]

        else:
            contact_ids = [panelist['contactId'] for panelist in self.history if panelist['status'] == value]
        return queryset.filter(qx_contact_id__in=contact_ids)
