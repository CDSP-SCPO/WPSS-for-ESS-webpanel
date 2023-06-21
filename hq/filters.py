# -- STDLIB
import re

# -- THIRDPARTY
import django_filters

# -- QXSMS
from panelist.models import Profile


class PanelistsHqFilter(django_filters.FilterSet):
    panelist_id_regex = re.compile(r'(\D*)(\d*)')
    id = django_filters.CharFilter(method='filter_panelist_id')

    class Meta:
        model = Profile
        fields = ['id', 'panel', 'is_opt_out', 'internet_use', 'sex']

    @property
    def qs(self):
        queryset = super().qs
        sort = '-' if self.request.GET.get('sort') == "desc" else ''
        order_by = self.request.GET.get('order_by', 'ess_id')

        if order_by == 'ess_id':
            order_args = [f'{sort}{key}' for key in ['country', 'ess_id']]

        elif order_by == 'year_of_birth':
            order_args = [f'{sort}{key}' for key in ['year_of_birth', 'month_of_birth', 'day_of_birth']]

        else:
            order_args = [f'{sort}{order_by}']

        return queryset.all().order_by(*order_args)

    def filter_panelist_id(self, queryset, name, value):
        country, ess_id = self.panelist_id_regex.search(value).groups()
        if ess_id:
            ess_id = int(ess_id)
        return queryset.filter(country__icontains=country, ess_id__icontains=ess_id)
