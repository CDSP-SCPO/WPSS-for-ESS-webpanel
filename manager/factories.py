# -- THIRDPARTY
import factory

# -- QXSMS
from manager.models import GroupTaskImport
from qxauth.factories import GroupFactory
from qxauth.models import User
from qxsms import settings


class ManagerFactory(factory.django.DjangoModelFactory):
    '''
    The call to ManagerFactory creates the Manager group if it does not exist yet,
    and adds the new manager to its group.
    '''
    class Meta:
        model = User
    email = factory.Sequence(lambda n: 'nc_{}@qxsms.com'.format(n))
    password = factory.PostGenerationMethodCall('set_password', 'nc')
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        group = GroupFactory(name=settings.QXSMS_GROUP_MANAGERS)
        self.groups.add(group)


class GroupTaskImportFactory(factory.django.DjangoModelFactory):
    '''
    Don't forget to attribute a panel instance when a GroupTaskImportFactory is created
    '''

    class Meta:
        model = GroupTaskImport
    celery_group_id = factory.Sequence(lambda n: '{}'.format(n + 1))
    file_name = factory.Sequence(lambda n: 'file_name_{}'.format(n + 1))
    dry_run = False
