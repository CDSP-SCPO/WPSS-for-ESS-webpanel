# -- DJANGO
from django.contrib import admin

# -- QXSMS (LOCAL)
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    search_fields = ['uid', 'ess_id', 'first_name', 'last_name', 'email', 'temp_email', 'phone', 'temp_phone']
    list_display = (
        'id',
        'user',
        'uid',
        'panel',
        'ess_id',
        'language',
        'first_name',
        'last_name',
        'email',
        'temp_email',
        'temp_email_expiry',
        'phone',
        'temp_phone',
        'temp_phone_expiry',
    )
    list_filter = (
        'panel',
        'language',
    )
