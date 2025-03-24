from django import template
from django.contrib.messages import INFO, SUCCESS, WARNING, ERROR

register = template.Library()

MESSAGE_COLORS = {
    INFO: "bg-blue-200 text-blue-800 border border-blue-300",
    SUCCESS: "bg-green-200 text-green-800 border border-green-300",
    WARNING: "bg-orange-200 text-orange-800 border border-orange-300",
    ERROR: "bg-red-200 text-red-800 border border-red-300",
}


@register.filter
def map_message_colors(level):
    return MESSAGE_COLORS.get(level, "bg-gray-200 text-gray-800")
