# -- STDLIB
from io import BytesIO

# -- DJANGO
from django.test import RequestFactory, TestCase

# -- QXSMS
from hq.factories import PanelFactory
from hq.models import Panel

# -- QXSMS (LOCAL)
from ..forms import CSVImportForm, PanelUpdateForm


class CSVImportFormTestCase(TestCase):

    def setUp(self):
        self.rf = RequestFactory()

    def test_file_not_closed_after_validation(self):
        csv_str = ','.join(CSVImportForm.fields) + '\n'
        csv_file = BytesIO(csv_str.encode('utf8'))
        # django.forms.fileds.FileField expects name and size attributes
        csv_file.name = 'data.csv'
        csv_file.size = len(csv_str)
        form = CSVImportForm(files={'dataset': csv_file})
        self.assertTrue(form.is_valid())
        self.assertFalse(csv_file.closed)

    # TODO
    def test_clean_headers(self):
        """Normalizes headers by lowercasing and removing whitespace"""
        # dirty = ['First_Name   ', '  Last_name']
        # clean = ['first_name', 'last_name']
        pass

    # TODO
    def test_invalid_empty_csv(self):
        """Empty CSV file"""
        pass

    # TODO
    def test_valid_sloppy_headers(self):
        """Validation succeeds with sloppily typed headers"""
        # _csv = "first_Name, Last_name,\tEmail,language\na,A,a@A.fr,FR\n"
        pass

    # TODO
    def test_invalid_missing_headers(self):
        """Validation fails if header fields are missing"""
        pass


class PanelUpdateFormTestCase(TestCase):
    def test_panel_update_form(self):
        panel = PanelFactory()
        self.assertFalse(panel.incentive_amount)
        self.assertFalse(panel.contact_info)
        incentive_amount = "5€"
        contact_info = "HELP YOURSELF"
        form = PanelUpdateForm({
            'incentive_amount': incentive_amount,
            'contact_info': contact_info,
        })
        self.assertTrue(form.is_valid())
        instance: Panel = form.save()
        self.assertEqual(instance.incentive_amount, incentive_amount)
        self.assertEqual(instance.contact_info, contact_info)
