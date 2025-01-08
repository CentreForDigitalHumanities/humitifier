import random
from datetime import datetime

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

    wild_wasteland = False
    if user.is_authenticated:
        wild_wasteland = user.wild_wasteland_mode

    oidc_enabled = hasattr(settings, "OIDC_RP_CLIENT_ID")
    gitlab_gag = False

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
            "Needs more cowbell",
            "Hum-IT CMDB",
            "Made for Itanium™",
            "I'm on a horse",
            "Keep calm and reboot",
            "Is it plugged in?",
            "Running on hope and caffeine",
            "Results may vary",
            "As seen on TV",
            "Not a flamethrower",
            "Some assembly required",
            "100% Functional Guarantee until it breakage",
            "Do not use if seal is broken",
            "Objects in mirror may be closer than they appear",
            "Your wish is our segfault",
        ]
        tag_line = random.choice(jokes)

        if (
            datetime.today().weekday() == 3 and random.randint(1, 100) == 1
        ):  # 3 is Thursday (Monday=0)
            gitlab_gag = True

    return {
        "layout": {
            "num_hosts": hosts.count(),
            "num_info_alerts": all_alerts.filter(level=AlertLevel.INFO).count(),
            "num_warning_alerts": all_alerts.filter(level=AlertLevel.WARNING).count(),
            "num_critical_alerts": all_alerts.filter(level=AlertLevel.CRITICAL).count(),
            "oidc_enabled": oidc_enabled,
            "wild_wasteland": wild_wasteland,
            "gitlab_gag": gitlab_gag,
            "tag_line": tag_line,
        }
    }
