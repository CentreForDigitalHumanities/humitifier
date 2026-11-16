from datetime import datetime, timedelta

from django import template
from django.template.defaultfilters import filesizeformat
from django.utils.timesince import timesince

from ..search.columns import format_value

register = template.Library()


@register.filter()
def format_search_value(value):
    return format_value(value)


@register.filter()
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter()
def size_from_kb(value, **kwargs):
    # We get the value in KB, but filesizeformat expects bytes
    return filesizeformat(value * 1024)


@register.filter()
def size_from_mb(value, **kwargs):
    # We get the value in MB, but filesizeformat expects bytes
    return filesizeformat(value * 1024 * 1024)


@register.filter()
def uptime(time_in_seconds: float, reference: datetime):

    try:
        startup_datetime = reference - timedelta(seconds=time_in_seconds)
    except TypeError:
        return "Failed to parse uptime"

    return timesince(startup_datetime, reference)
