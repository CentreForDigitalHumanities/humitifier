from django import template
from django.http import QueryDict
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def param_replace(context, **kwargs):
    """
    Return encoded URL parameters that are the same as the current
    request's parameters, only with the specified GET parameters added or changed.

    It also removes any empty parameters to keep things neat,
    so you can remove a parm by setting it to ``""``.

    For example, if you're on the page ``/things/?with_frosting=true&page=5``,
    then

    <a href="/things/?{% param_replace page=3 %}">Page 3</a>

    would expand to

    <a href="/things/?with_frosting=true&page=3">Page 3</a>

    Based on
    https://stackoverflow.com/questions/22734695/next-and-before-links-for-a-django-paginated-query/22735278#22735278
    """
    d = context["request"].GET.copy()
    for k, v in kwargs.items():
        d[k] = v
    for k in [k for k, v in d.items() if not v]:
        del d[k]
    return mark_safe(d.urlencode())


@register.simple_tag
def filter_params(filterset, **kwargs):
    """
    Return encoded URL parameters containing only the active filters from a
    django-filter FilterSet, with specified parameters added, changed, or removed.
    """
    d = QueryDict(mutable=True)
    if filterset and filterset.data:
        for field in filterset.filters:
            if field in filterset.data:
                values = [v for v in filterset.data.getlist(field) if v]
                if values:
                    d.setlist(field, values)
    for k, v in kwargs.items():
        if v:
            d[k] = str(v)
        else:
            d.pop(k, None)
    return mark_safe(d.urlencode())
