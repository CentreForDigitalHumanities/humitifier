from datetime import datetime, timedelta

from django import template
from django.template.defaultfilters import filesizeformat
from django.utils.timesince import timesince

register = template.Library()


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

    startup_datetime = reference - timedelta(seconds=time_in_seconds)

    return timesince(startup_datetime, reference)