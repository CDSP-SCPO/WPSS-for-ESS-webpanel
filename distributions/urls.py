# -- DJANGO
from django.urls import include, path

# -- QXSMS (LOCAL)
from . import views

app_name = 'dist'

msgd_patterns = [
    path('', views.MessageDistributionList.as_view(), name='list'),
    path('create/email', views.EmailDistributionCreate.as_view(), name='create-email'),
    path('create/sms', views.SMSDistributionCreate.as_view(), name='create-sms'),
    path('<int:pk>/', views.MessageDistributionDetail.as_view(), name='detail'),
    path('<int:pk>/fallback', views.MessageDistributionFallbackCreate.as_view(), name='create-fallback'),
    path('<int:pk>/send', views.MessageDistributionSend.as_view(), name='send'),
    path('<int:pk>/delete', views.MessageDistributionDelete.as_view(), name='delete'),
    path('<int:pk>/update', views.MessageDistributionUpdate.as_view(), name='update'),
]

urlpatterns = [
    path('', views.LinkDistributionList.as_view(), name='list'),
    path('create/', views.LinkDistributionCreate.as_view(), name='create'),
    path('<int:pk>/', views.LinkDistributionDetail.as_view(), name='detail'),
    path('<int:pk>/generate/', views.LinkDistributionGenerate.as_view(), name='generate'),
    path('<int:pk>/delete/', views.LinkDistributionDelete.as_view(), name='delete'),
    path('<int:pk>/history', views.LinkDistributionHistory.as_view(), name='history'),
    # I wanted to refer to 'msgd' views as 'dist:msgd:<name>'.
    # Inclusion below does the trick, but I don't really understand how yet...
    path('msgd/', include((msgd_patterns, 'dist'), namespace='msgd'))
]
