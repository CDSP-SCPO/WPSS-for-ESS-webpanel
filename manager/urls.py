# -- DJANGO
from django.urls import path

# -- QXSMS
from utils.views import blank_slot_export_csv

# -- QXSMS (LOCAL)
from .views import (
    BlankSlotValueImportCsv, BlankSlotValueList, BlankSlotValueUpdate, Home,
    LinkDistributionExport, ManagerProfileUpdate, MemberList,
    MessageDistributionDetail, MessageDistributionList, PanelDetail, PanelList,
    PanelSurveyDetail, PanelSurveyList, PanelUpdate, ProfileCreate,
    ProfileDeactivate, ProfileDelete, ProfileExportCsv, ProfileExportCustomCsv,
    ProfileImportCsv, ProfilePasswordReset, ProfileUpdate, TaskImportDetail,
    TaskImportList, download_sms_stats, members_import_csv_sample,
)

app_name = 'manager'
urlpatterns = [
    path('', Home.as_view(), name='home'),
    path('profile/', ManagerProfileUpdate.as_view(), name='profile-update'),
    # PANELS
    path('panels/', PanelList.as_view(), name='panel-list'),
    path('panels/<int:pk>/', PanelDetail.as_view(), name='panel-detail'),
    path('panels/<int:pk>/update/', PanelUpdate.as_view(), name='panel-update'),
    path('panels/<int:pk>/members/', MemberList.as_view(), name='panel-member-list'),
    path('panels/<int:pk>/members/create/', ProfileCreate.as_view(), name='panel-member-create'),
    path('panels/<int:pk>/members/import/', ProfileImportCsv.as_view(), name='panel-member-import'),
    path('panels/<int:pk>/members/export/', ProfileExportCsv.as_view(), name='panel-member-export'),
    path('panels/<int:panel_pk>/members/export/blankslot/', blank_slot_export_csv, name='panel-blank-slot-export'),
    path('panels/<int:pk>/members/import/blankslot/', BlankSlotValueImportCsv.as_view(),
         name='panel-blank-slot-import'),
    path('panels/<int:pk>/members/export/custom', ProfileExportCustomCsv.as_view(),
         name='panel-member-export-custom'),
    path('panels/<int:pk>/surveys/', PanelSurveyList.as_view(), name='panel-survey-list'),
    path('panels/<int:pk>/surveys/<int:linkdistribution_pk>/export', LinkDistributionExport.as_view(),
         name='panel-survey-links-export'),
    path('panels/<int:pk>/surveys/<int:linkdistribution_pk>/', PanelSurveyDetail.as_view(),
         name='panel-survey-detail'),
    # BLANK SLOTS VALUES
    path('members/<int:pk>/blankslotvalues/', BlankSlotValueList.as_view(), name='blankslotvalue-list'),
    path('members/<int:pk>/blankslotvalues/update/', BlankSlotValueUpdate.as_view(),
         name='blankslotvalue-update'),
    # MEMBERS
    path('members/<int:pk>/update/', ProfileUpdate.as_view(), name='panel-member-update'),
    path('members/<int:pk>/delete/', ProfileDelete.as_view(), name='panel-member-delete'),
    path('members/<int:pk>/disable/', ProfileDeactivate.as_view(), name='panel-member-deactivate'),
    path('members/<int:pk>/password-change/reset/', ProfilePasswordReset.as_view(),
         name='panel-member-password-reset'),
    # SAMPLES
    path('samples/members/import/', members_import_csv_sample, name='members-import-sample'),
    # TASKS
    path('panels/<int:pk>/import/list/', TaskImportList.as_view(), name='task-import-list'),
    path('panels/<int:pk>/import/detail/<int:task_pk>/', TaskImportDetail.as_view(), name='task-import-detail'),
    # API
    # MESSAGE DISTRIBUTIONS
    path('panels/<int:pk>/msgdist/', MessageDistributionList.as_view(), name='msg-distribution-list'),
    path('panels/<int:pk>/msgdist/<int:msgdist_pk>/', MessageDistributionDetail.as_view(),
         name='msg-distribution-detail'),
    path('panels/<int:panel_pk>/msgdist/<int:msgdist_pk>/smsstatscsv/', download_sms_stats,
         name='msg-distribution-dlsmsstats'),
]
