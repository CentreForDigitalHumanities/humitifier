from django import template
from django.contrib.messages import INFO, SUCCESS, WARNING, ERROR

register = template.Library()

MESSAGE_COLORS = {
    INFO: "border-blue-500 bg-blue-100 text-blue-900 dark:bg-blue-950/60 dark:text-blue-200",
    SUCCESS: "border-green-500 bg-green-100 text-green-900 dark:bg-green-950/60 dark:text-green-200",
    WARNING: "border-orange-500 bg-orange-100 text-orange-900 dark:bg-orange-950/60 dark:text-orange-200",
    ERROR: "border-red-500 bg-red-100 text-red-900 dark:bg-red-950/60 dark:text-red-200",
}


@register.filter
def map_message_colors(level):
    return MESSAGE_COLORS.get(level, "bg-gray-200 text-gray-800")
