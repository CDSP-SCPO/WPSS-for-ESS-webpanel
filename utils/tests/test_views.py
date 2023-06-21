# -- DJANGO
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TransactionTestCase

# -- QXSMS
from panelist.factories import PanelistFactory
from panelist.models import BlankSlot, BlankSlotValue

# -- QXSMS (LOCAL)
from ..views import BaseBlankSlotValueUpdate

User = get_user_model()


class BaseBlankSlotValueUpdateTestCase(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class TestView(BaseBlankSlotValueUpdate):
            template_name = ''

            def get_success_url(self):
                return '/success'
        cls.view_class = TestView

    def setUp(self):
        self.view = self.view_class.as_view()
        self.rf = RequestFactory()
        self.profile = PanelistFactory()

    def test_get(self):
        request = self.rf.get('/')
        response = self.view(request, pk=self.profile.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIn('formset', response.context_data)

    def test_create(self):
        bk = BlankSlot.objects.create(name='blank_slot_name', description='blank_slot_description')
        request = self.rf.post('/', data={
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '',
            'form-0-value': 'new_value',
            'form-0-blankslot': bk.pk
        })
        response = self.view(request, pk=self.profile.pk)
        self.assertRedirects(response, '/success', fetch_redirect_response=False)
        self.assertEqual(BlankSlotValue.objects.count(), 1)

    def test_update(self):
        bk = BlankSlot.objects.create(name='blank_slot_name', description='blank_slot_description')
        bsv = BlankSlotValue.objects.create(blankslot=bk, profile=self.profile, value='test_value')
        request = self.rf.post('/', {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-MAX_NUM_FORMS': '',
            'form-0-value': 'updated_value',
            'form-0-id': bsv.pk
        })
        response = self.view(request, pk=self.profile.pk)
        self.assertRedirects(response, '/success', fetch_redirect_response=False)
        self.assertEqual(BlankSlotValue.objects.count(), 1)
        bsv.refresh_from_db()
        self.assertTrue(bsv.value, 'test_value')

    def test_delete(self):
        bk = BlankSlot.objects.create(name='blank_slot_name', description='blank_slot_description')
        bsv = BlankSlotValue.objects.create(blankslot=bk, profile=self.profile, value='foo')
        request = self.rf.post('/', {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-MAX_NUM_FORMS': '',
            'form-0-value': 'foo',
            'form-0-id': bsv.pk,
            'form-0-DELETE': 'on'
        })
        response = self.view(request, pk=self.profile.pk)
        self.assertRedirects(response, '/success', fetch_redirect_response=False)
        self.assertEqual(BlankSlotValue.objects.count(), 0)

    def test_create_update_delete(self):
        bks = [BlankSlot(name=f"bs-{i}", description="foo") for i in range(3)]
        bks = BlankSlot.objects.bulk_create(bks)
        to_update = BlankSlotValue.objects.create(blankslot=bks[0], profile=self.profile, value='to_update')
        to_delete = BlankSlotValue.objects.create(blankslot=bks[1], profile=self.profile, value='to_delete')
        request = self.rf.post('/', {
            'form-TOTAL_FORMS': '3',
            'form-INITIAL_FORMS': '2',
            'form-MAX_NUM_FORMS': '',
            'form-0-value': 'updated',
            'form-0-id': to_update.pk,
            'form-1-id': to_delete.pk,
            'form-1-DELETE': 'on',
            'form-2-value': 'created',
            'form-2-blankslot': bks[2].pk
        })
        response = self.view(request, pk=self.profile.pk)
        self.assertRedirects(response, '/success', fetch_redirect_response=False)
        self.assertEqual(BlankSlotValue.objects.count(), 2)
        to_update.refresh_from_db()
        self.assertEqual(to_update.value, 'updated')
        with self.assertRaises(BlankSlotValue.DoesNotExist):
            BlankSlotValue.objects.get(value='to_delete')
