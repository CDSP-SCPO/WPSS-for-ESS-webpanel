# -- DJANGO
from django.urls import path

# -- QXSMS
from hq.views import (
    BlankSlotCreate, BlankSlotDelete, BlankSlotImportCsv, BlankSlotList,
    BlankSlotUpdate, BlankSlotValueList, BlankSlotValueUpdate,
    EmailDistributionCreate, Home, HqProfileUpdate, LinkDistributionCreate,
    LinkDistributionDelete, LinkDistributionDetail, LinkDistributionGenerate,
    LinkDistributionList, ManagerCreate, ManagerDelete, ManagerList,
    ManagerUpdate, MessageDistributionDelete, MessageDistributionDetail,
    MessageDistributionFallbackCreate, MessageDistributionHistory,
    MessageDistributionList, MessageDistributionSend,
    MessageDistributionUpdate, MessageList, PanelCreate, PanelDetail,
    PanelList, PanelManagerAssign, PanelManagerUnassign, PanelmemberList,
    PanelUpdate, ProfileExportCSV, SMSDistributionCreate, SurveyList,
    download_sms_stats,
)
from utils.views import blank_slot_export_csv

app_name = 'hq'
urlpatterns = [
    path('', Home.as_view(), name='home'),
    path('profile/', HqProfileUpdate.as_view(), name='profile-update'),
    path('panelmembers/', PanelmemberList.as_view(), name='panelmember-list'),
    # SURVEYS
    path('surveys/', SurveyList.as_view(), name='survey-list'),
    # PANELS
    path('panels/', PanelList.as_view(), name='panel-list'),
    path('panels/create/', PanelCreate.as_view(), name='panel-create'),
    path('panels/<int:pk>/', PanelDetail.as_view(), name='panel-detail'),
    path('panels/<int:pk>/update/', PanelUpdate.as_view(), name='panel-update'),
    path('panels/<int:pk>/assign/', PanelManagerAssign.as_view(), name='panel-assign'),
    path('panels/<int:pk>/unassign/', PanelManagerUnassign.as_view(), name='panel-unassign'),
    # BLANK SLOTS
    path('blankslot/', BlankSlotList.as_view(), name='blankslot-list'),
    path('blankslot/create', BlankSlotCreate.as_view(), name='blankslot-create'),
    path('blankslot/<int:pk>/update/', BlankSlotUpdate.as_view(), name='blankslot-update'),
    path('blankslot/<int:pk>/delete', BlankSlotDelete.as_view(), name='blankslot-delete'),
    path('panelmembers/<int:pk>/blankslotvalues/', BlankSlotValueList.as_view(), name='blankslotvalue-list'),
    path('panelmembers/<int:pk>/blankslotvalues/update', BlankSlotValueUpdate.as_view(), name='blankslotvalue-update'),
    # MANAGERS
    path('managers/', ManagerList.as_view(), name='manager-list'),
    path('managers/create/', ManagerCreate.as_view(), name='manager-create'),
    path('managers/<int:pk>/update/', ManagerUpdate.as_view(), name='manager-update'),
    path('managers/<int:pk>/delete/', ManagerDelete.as_view(), name='manager-delete'),
    # MESSAGES
    path('messages/', MessageList.as_view(), name='message-list'),
    # EXPORT
    path('panelist/export/', ProfileExportCSV.as_view(), name='panelist-export'),
    path('blankslot/import/', BlankSlotImportCsv.as_view(), name='blank-slot-import'),
    path('blankslot/export/', blank_slot_export_csv, name='blank-slot-export'),
    # LINK DISTRIBUTIONS
    path('links/', LinkDistributionList.as_view(), name='link-distribution-list'),
    path('links/create/', LinkDistributionCreate.as_view(), name='link-distribution-create'),
    path('links/<int:pk>/', LinkDistributionDetail.as_view(), name='link-distribution-detail'),
    path('links/<int:pk>/delete/', LinkDistributionDelete.as_view(), name='link-distribution-delete'),
    path('links/<int:pk>/generate/', LinkDistributionGenerate.as_view(), name="link-distribution-generate"),
    # MESSAGE DISTRIBUTIONS
    path('msgdist/', MessageDistributionList.as_view(), name='msg-distribution-list'),
    path('msgdist/<int:pk>/', MessageDistributionDetail.as_view(), name='msg-distribution-detail'),
    path('msgdist/<int:pk>/smsstatscsv/', download_sms_stats, name='msg-distribution-dlsmsstats'),
    path('msgdist/create/email/', EmailDistributionCreate.as_view(), name='email-distribution-create'),
    path('msgdist/<int:pk>/delete/', MessageDistributionDelete.as_view(), name='msg-distribution-delete'),
    path('msgdist/create/sms/', SMSDistributionCreate.as_view(), name='sms-distribution-create'),
    path('msgdist/<int:pk>/send/', MessageDistributionSend.as_view(), name='msg-distribution-send'),
    path('msgdist/<int:pk>/panels/<int:panel_pk>/history/',
         MessageDistributionHistory.as_view(), name='msg-distribution-history'),
    path("msgdist/<int:pk>/fallback/", MessageDistributionFallbackCreate.as_view(),
         name='msg-distribution-fallback-create'),
    path('msgdist/<int:pk>/update/', MessageDistributionUpdate.as_view(), name='msg-distribution-update'),

]
