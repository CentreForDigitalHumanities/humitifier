import random
from datetime import datetime

from django.conf import settings
from django.utils.safestring import mark_safe

from alerting.models import Alert, AlertSeverity
from hosts.models import Host


def layout_context(request):
    """This function is used to add data to the template-context for all views.
    It adds all the little nuggets of data the base template displays.
    """
    user = request.user

    hosts = Host.objects.get_for_user(user).exclude(archived=True)
    all_alerts = Alert.objects.get_for_user(user).filter(acknowledgement=None)

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
            "Humanities-IT Services Systems Team Labs ICT Configuration Management Database Status Viewer Application",
            "Made for Itanium™",
            "I'm on a horse",
            "Keep calm and reboot",
            "Is it plugged in?",
            "Running on hope and caffeine",
            "Results may vary",
            "As seen on TV",
            "Not a flamethrower",
            "Some assembly required",
            "100% Functional Guarantee until it breaks",
            "Do not use if seal is broken",
            "Do not use if seal is unbroken",
            "Objects in mirror may be closer than they appear",
            "Your wish is our segfault",
            "Not a humidifier",
            "We've been trying to contact you about your servers extended warranty",
            "CAUTION: This site originated from inside of Utrecht University. Do click links or open attachments unless you recognize the sender or know the content is unsafe.",
            "Do you hear wolves?",
            "Я просто пташка",
            mark_safe("- What is my purpose?<br/>- You pass butter"),
            "Have a break, have a Humitifier",  # Credits: some weird shopify tool
            "E",
            "Are you even reading this?",
            "Finland has the most heavy metal bands per capita",
            "A cat's ear contains 32 muscles",
            "Ravens know when someone is spying on them",
            "Flamingos can only eat with their heads upside down",
            "A group of crows is a 'murder'",
            "In the 1870s, cats were being trained in Belgium to deliver mail to replace homing pigeons",
            "Antarctica’s international telephone dialling code is +672",
            "Thousands of rabbits once attacked Napoleon. The rabbits won.",
            "There’s a tiny home in Virginia called the “Spite House” because that’s why it was built",
            "Playing dance music can help ward off mosquitoes",
            "“Avoid potential systems fans loop logs” - GPT-4o, 2025",
            "Trotse winnaar van de SPrins 'Gouden API' award 🏆",
        ]
        tag_line = random.choice(jokes)

        if (
            datetime.today().weekday() == 3 and random.randint(1, 100) == 1
        ):  # 3 is Thursday (Monday=0)
            gitlab_gag = True

    return {
        "layout": {
            "num_hosts": hosts.count(),
            "num_info_alerts": all_alerts.filter(severity=AlertSeverity.INFO).count(),
            "num_warning_alerts": all_alerts.filter(
                severity=AlertSeverity.WARNING
            ).count(),
            "num_critical_alerts": all_alerts.filter(
                severity=AlertSeverity.CRITICAL
            ).count(),
            "oidc_enabled": oidc_enabled,
            "wild_wasteland": wild_wasteland,
            "gitlab_gag": gitlab_gag,
            "tag_line": tag_line,
            "humitifier_version": settings.HUMITIFIER_VERSION,
        }
    }
