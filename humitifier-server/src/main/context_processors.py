import random

from django.conf import settings

from hosts.models import Alert, AlertLevel, Host


def layout_context(request):
    """This function is used to add data to the template-context for all views.
    It adds all the little nuggets of data the base template displays.
    """
    user = request.user

    hosts = Host.objects.get_for_user(user).exclude(archived=True)
    all_alerts = Alert.objects.get_for_user(user)

    tag_line = "HumIT CMDB"

    wild_wasteland = settings.DEBUG  # TODO: user setting

    if wild_wasteland:
        jokes = [
            "Performs best on a 386",
            "Now with 100% more bugs!",
            "Performance edition",
            "I like trains",
            "Prrrrrrrrrr",
            "May contain traces of nuts",
            "Caution: Do not eat",
            "Don't look at me!",
            "Who watches the watchmen?",
            "How are you?",
            "CAUTION: This email originated from outside of Utrecht University. Do not click links or open attachments unless you recognize the sender and know the content is safe.",
        ]
        tag_line = random.choice(jokes)

    return {
        "layout": {
            "num_hosts": hosts.count(),
            "num_info_alerts": all_alerts.filter(level=AlertLevel.INFO).count(),
            "num_warning_alerts": all_alerts.filter(level=AlertLevel.WARNING).count(),
            "num_critical_alerts": all_alerts.filter(level=AlertLevel.CRITICAL).count(),
            "wild_wasteland": wild_wasteland,
            "tag_line": tag_line,
        }
    }