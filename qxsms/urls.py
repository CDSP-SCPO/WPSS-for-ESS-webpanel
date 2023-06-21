# -- DJANGO
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path

# -- QXSMS
from panelist.views import EmailChangeConfirm, PhoneChangeConfirm
from qxauth.views import (
    GroupLogin, PasswordChange, PasswordReset, PasswordResetConfirm,
)
from qxsms import settings

app_name = 'qxsms'
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', GroupLogin.as_view(), name='login'),
    path('password-change/', PasswordChange.as_view(), name='password-change'),
    path('password-change/reset/', PasswordReset.as_view(), name='password-reset'),
    path('password-change/reset/<str:uidb64>/<str:token>/', PasswordResetConfirm.as_view(),
         name='password-reset-confirm'),
    path('email-change/<str:uidb64>/<str:token>/', EmailChangeConfirm.as_view(),
         name='email-change-confirm'),
    path('phone-change/<str:uidb64>/<str:token>/', PhoneChangeConfirm.as_view(),
         name='phone-change-confirm'),
    path('p/', include('panelist.urls')),
    path('m/', include('manager.urls')),
    path('hq/', include('hq.urls')),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('utils/', include('utils.urls')),
]

if settings.DEBUG:
    import debug_toolbar  # isort:skip

    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
        path('hijack/', include('hijack.urls', namespace='hijack')),
        path('dist/', include('distributions.urls'))
    ]
