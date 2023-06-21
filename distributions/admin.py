# -*- coding: utf-8 -*-
# -- DJANGO
from django.contrib import admin

# -- QXSMS (LOCAL)
from .models import LinkDistribution, MessageDistribution


class ReadOnlyAdminMixin:
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LinkDistribution)
class LinkDistributionAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('short_uid', 'get_panels', 'survey', 'expiration_date', 'qx_created_date')
    search_fields = ('uid',)
    fields = ('description', 'expiration_date', 'survey', 'panels')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('panels').all()

    def get_panels(self, obj):
        """
        Django admin doesn't allow directly to add m2m fields
        """
        return "\n".join([str(p) for p in obj.panels.all()])


@admin.register(MessageDistribution)
class MessageDistributionAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('short_uid', 'link_distribution', 'contact_mode', 'send_date', 'subject')
    search_fields = ('uid',)
