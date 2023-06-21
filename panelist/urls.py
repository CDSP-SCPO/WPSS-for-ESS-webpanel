# -- DJANGO
from django.urls import path

# -- QXSMS
from panelist.views import (
    EmailChangeView, Help, Home, LinkListView, PhoneChangeView, ProfileUpdate,
)

app_name = 'panelist'
urlpatterns = [
    path('', Home.as_view(), name='home'),
    path('surveys/', LinkListView.as_view(), name='survey-list'),
    path('help/', Help.as_view(), name='help'),
    path('profile/', ProfileUpdate.as_view(), name='profile-update'),
    path('email-change/', EmailChangeView.as_view(), name='email-change'),
    path('phone-change/', PhoneChangeView.as_view(), name='phone-change'),
]
