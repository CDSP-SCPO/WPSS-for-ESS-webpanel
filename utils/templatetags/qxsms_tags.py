# -- STDLIB
import json
from urllib import parse

# -- DJANGO
from django import template
from django.contrib.staticfiles.finders import find
from django.core.serializers.json import DjangoJSONEncoder
from django.template import Context, Template
from django.template.defaulttags import url
from django.utils.safestring import mark_safe

# -- QXSMS
from utils.csvimport import FIELD_MAP

register = template.Library()


@register.inclusion_tag('utils/icon.html')
def icon(name, extra_class=None, title=None):
    path = f"icons/{name}.svg"
    return {"path": path, "extra_class": extra_class, "title": title}


@register.simple_tag
def svg(path):
    file = find(path)
    return mark_safe(open(file, 'r').read())


class BreadcrumbNode(template.Node):
    def __init__(self, nodelist, url_node):
        self.nodelist = nodelist
        self.url_node = url_node

    def render(self, context):
        path = None
        if self.url_node:
            path = self.url_node.render(context)

        content = self.nodelist.render(context)

        fp = open('utils/templates/utils/breadcrumb_item.html')
        t = Template(fp.read())
        fp.close()

        html = t.render(Context({'content': content, 'url': path}))

        return html


@register.tag
def breadcrumbitem(parser, token):
    bits = token.split_contents()
    url_node = None
    if len(bits) >= 2:
        url_node = url(parser, token)
    nodelist = parser.parse(('endbreadcrumbitem',))
    parser.delete_first_token()
    return BreadcrumbNode(nodelist, url_node)


_json_script_escapes = {
    ord('>'): '\\u003E',
    ord('<'): '\\u003C',
    ord('&'): '\\u0026',
}


@register.filter(name='json', is_safe=True)
def json_dump(value, only_keys: str = ''):
    if only_keys and not isinstance(value, dict):
        raise Exception("Cannot use only_keys if value is not a dict")
    if only_keys:
        only_keys = only_keys.split(',')
        value = {k: value[k] for k in value.keys() if k in only_keys}
    json_str = json.dumps(value, cls=DjangoJSONEncoder).translate(_json_script_escapes)
    return json_str


class NoTransNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context)
        return output


@register.simple_tag
def get_csv_field_name(field):
    return FIELD_MAP.get(field, field)


@register.simple_tag
def add_url_params(url, **kwargs):
    """Add get params to an URL. The params passed as kwargs will replace those already present in the URL."""
    pr = parse.urlparse(url)
    query = parse.parse_qs(pr.query)
    query.update(**kwargs)
    return parse.urlunparse(pr._replace(query=parse.urlencode(query, doseq=True)))
