from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def indicator_pill(color: str, label: str):
    css_colors = f"border border-{color}-500/40 bg-{color}-200 dark:bg-{color}-900 text-{color}-950 dark:text-{color}-100"
    return mark_safe(f"""
<div class="px-3 py-1 inline-block mr-3 rounded-sm {css_colors} font-semibold">
    {label}
</div>
""")


@register.simple_tag
def green_indicator_pill(label: str):
    return indicator_pill(
        "green",
        label,
    )


@register.simple_tag
def red_indicator_pill(label: str):
    return indicator_pill(
        "red",
        label,
    )
