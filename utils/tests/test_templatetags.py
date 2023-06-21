# -- DJANGO
from django.template import Context, Template
from django.test import TestCase

# -- QXSMS
from utils.templatetags.qxsms_tags import (
    add_url_params, get_csv_field_name, json_dump,
)


class TemplateTagsTestCase(TestCase):
    def test_json_dump(self):
        self.assertEqual(json_dump({}), '{}')
        with self.assertRaises(Exception):
            json_dump([], only_keys='test')

        self.assertEqual(json_dump(['toto']), '["toto"]')
        self.assertEqual(json_dump({
            'foo': 1,
            'bar': 2,
            'foobar': 2,
        }, only_keys='foo,bar'), '{"foo": 1, "bar": 2}')

    def test_get_csv_field_name(self):
        self.assertEqual(get_csv_field_name('ess_id'), 'idno')
        self.assertEqual(get_csv_field_name('test'), 'test')

    def _template_assert_equal(self, template, context, result):
        t = Template("{% load qxsms_tags %}" + template)
        c = Context(context)
        self.assertEqual(t.render(c), result)

    def test_qx_lang(self):
        baseurl = "http://example.com/test"
        urllang = "http://example.com/test?Q_Language=EN"
        self.assertEqual(add_url_params(baseurl, Q_Language="EN"), urllang)
        self._template_assert_equal("{% add_url_params url Q_Language='EN'%}", {'lang': "EN", "url": baseurl}, urllang)
