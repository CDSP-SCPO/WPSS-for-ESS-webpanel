# -- DJANGO
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path

# -- QXSMS
from utils.views import ImportSMSStats, ImportSMSStatsEmail

app_name = 'utils'
urlpatterns = [
    path('import-sms-stats/', staff_member_required(ImportSMSStats.as_view()), name='import-sms-stats'),
    path('email-sms-stats/', staff_member_required(ImportSMSStatsEmail.as_view()), name='email-sms-stats'),
]
