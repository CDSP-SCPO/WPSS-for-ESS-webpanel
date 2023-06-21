# -- QXSMS
from panelist.models import Profile


def get_panelist_counts(object_list, grand_total_filters={}, grand_total_present=None):
    if not grand_total_present:
        grand_total = Profile.objects.filter(**grand_total_filters).count()
    else:
        grand_total = grand_total_present
    total = object_list.count()
    return {
        'grand_total': grand_total,
        'total': total,
    }
