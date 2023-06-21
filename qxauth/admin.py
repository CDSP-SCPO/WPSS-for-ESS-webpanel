# -- DJANGO
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin

# -- QXSMS
from qxauth.models import User


@admin.register(User)
class UserAdmin(DefaultUserAdmin):
    """
    Custom Admin because of username removal
    """

    @staticmethod
    def group_names(obj):
        return ','.join([g.name for g in obj.groups.all()]) if obj.groups.count() else ''

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('groups')

    fieldsets = (
        (None, {'fields': ('email', 'phone', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'phone', 'first_name', 'last_name', 'group_names', 'is_staff', 'is_superuser')
    search_fields = ('first_name', 'last_name', 'email', 'phone')
    ordering = ('email', 'phone')
    filter_horizontal = ('groups',)
