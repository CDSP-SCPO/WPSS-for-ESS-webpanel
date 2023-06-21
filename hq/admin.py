# -*- coding: utf-8 -*-
# -- DJANGO
from django.contrib import admin

# -- QXSMS (LOCAL)
from .models import Panel


@admin.register(Panel)
class PanelAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('id', 'name')
    list_filter = ('managers',)
    raw_id_fields = ('managers',)
