from django import template

register = template.Library()


@register.filter()
def strip_quotes(value, **kwargs):
    if not value:
        return value
    if value[0] == '"':
        value = value[1:]
    if value[-1] == '"':
        value = value[:-1]

    return value