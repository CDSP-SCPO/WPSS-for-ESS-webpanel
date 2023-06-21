# -- STDLIB
from datetime import timezone

# -- THIRDPARTY
import factory

# -- QXSMS (LOCAL)
from .models import (
    Link, LinkDistribution, Message, MessageDistribution, Survey,
)


class MessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Message
    qx_id = factory.Sequence(lambda n: 'message_qx_id_{}'.format(n))
    category = Message.EMAIL_INVITE
    description = factory.LazyAttribute(lambda n: 'description_{}'.format(n.qx_id))


class SubjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Message
    qx_id = factory.Sequence(lambda n: 'subject_qx_id_{}'.format(n))
    category = Message.EMAIL_SUBJECT
    description = factory.LazyAttribute(lambda n: 'description_{}'.format(n.qx_id))


class SurveyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Survey
    qx_id = factory.Sequence(lambda n: 'survey_qx_id_{}'.format(n))
    name = factory.LazyAttribute(lambda n: 'name_{}'.format(n.qx_id))


class LinkDistributionFactory(factory.django.DjangoModelFactory):
    '''
    Create automatically a survey
    Need 2 arguments:
        panels ==> list of panel(s) concerned by the distribution
        created ==> Boolean which allow (or not) to generate links associated to the Linkdistribution

    Exemple :
        manager = ManagerFactory()
        panelist = PanelistFactory(managers=[manager])

        link_distribution = LinkDistributionFactory(panels=[self.panelist.panel], create_links=True)
    '''

    class Meta:
        model = LinkDistribution
    survey = factory.SubFactory(SurveyFactory)
    qx_list_id = factory.Sequence(lambda n: 'qx_list_id_{}'.format(n))

    @factory.post_generation
    def panels(self, create, extracted, **kwargs):
        if extracted:
            self.panels.set(extracted)

    @factory.post_generation
    def create_links(self, create, extracted, **kwargs):
        if extracted:
            self.save_links()


class LinkFactory(factory.django.DjangoModelFactory):
    '''
    LinkFactory has no reason to be called in the tests
    This class is useful when MessageDistributionFactory is called
    '''

    class Meta:
        model = Link
    distribution = factory.SubFactory(LinkDistributionFactory)
    profile = factory.SubFactory('panelist.factories.PanelistFactory')
    qx_contact_id = factory.Sequence(lambda n: 'CID_{}'.format(n+1))


class MessageDistributionFactory(factory.django.DjangoModelFactory):
    '''
    The correct way to use this class is to first create a panelist and a linkdistribution,
    then call them as parameters

    Ex :
        - 1 panelist and 1 panel:
            manager = ManagerFactory()
            panelist = PanelistFactory(panel__managers=[manager])
            link_distribution = LinkDistributionFactory(panels=[self.panelist.panel], create_links=True)
            message_distribution = MessageDistributionFactory(link_distribution=link_distribution,
                                                              links=link_distribution.links.all())

        - 2 panelist and 2 panel:
            manager = ManagerFactory()
            panelist1 = PanelistFactory(panel__managers=[manager])
            panelist2 = PanelistFactory(panel__managers=[manager])
            link_distribution = LinkDistributionFactory(panels=[self.panelist1.panel, self.panelist2.panel],
                                                        create_links=True)
            message_distribution = MessageDistributionFactory(link_distribution=link_distribution,
                                                              links=link_distribution.links.all())
    '''

    class Meta:
        model = MessageDistribution

    subject = factory.SubFactory(SubjectFactory)
    message = factory.SubFactory(MessageFactory)
    link_distribution = factory.SubFactory(LinkDistributionFactory)
    target = MessageDistribution.TARGET_ALL
    contact_mode = MessageDistribution.MODE_EMAIL
    send_date = factory.Faker('date_time', tzinfo=timezone.utc)

    @factory.post_generation
    def links(self, create, extracted, **kwargs):
        if extracted:
            self.links.set(extracted)
