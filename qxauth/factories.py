# -- DJANGO
from django.contrib.auth.models import Group

# -- THIRDPARTY
import factory


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group
        django_get_or_create = ('name',)
    name = ''
