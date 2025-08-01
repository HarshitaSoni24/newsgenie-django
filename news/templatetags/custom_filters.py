# C:\Users\GANESH CHOUDHARY\bytenews\news\templatetags\custom_filters.py

from django import template
from urllib.parse import urlencode # New import for url encoding

register = template.Library()

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Replaces or adds GET parameters in the current URL's query string.
    Usage: {% url_replace request param_name='new_value' %}
    Note: You pass kwargs like `page=1`, `category='Sports'`.
    """
    d = context['request'].GET.copy()
    for k, v in kwargs.items():
        d[k] = v
    # Remove empty parameters to keep URLs clean
    for k in [key for key, value in d.items() if not value]:
        del d[k]
    return d.urlencode() # Use urlencode directly from QueryDict