# -- THIRDPARTY
import factory

# -- QXSMS
from qxauth.factories import GroupFactory
from qxauth.models import User
from qxsms import settings

# -- QXSMS (LOCAL)
from .models import Panel


class PanelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Panel

    name = factory.Sequence(lambda n: f'Panel {n}')

    @factory.post_generation
    def managers(self, create, extracted, **kwargs):
        if extracted:
            self.managers.set(extracted)


class HqFactory(factory.django.DjangoModelFactory):
    '''
    The call to HqFactory creates the HQ group if it does not exist yet,
    and adds the new hq to its group.
    '''
    class Meta:
        model = User
    email = factory.Sequence(lambda n: 'hq_{}@qxsms.com'.format(n))
    password = factory.PostGenerationMethodCall('set_password', 'hq')
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        group = GroupFactory(name=settings.QXSMS_GROUP_ADMINS)
        self.groups.add(group)
