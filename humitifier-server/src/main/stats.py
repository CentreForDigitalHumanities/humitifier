from datetime import date
import random

from django.db.models import Count, Q

from alerting.models import Alert, AlertSeverity
from hosts.models import Host


def get_os_stats(user):
    return (
        Host.objects.get_for_user(user)
        .filter(archived=False)
        .values("os")
        .annotate(count=Count("os"))
    )


def get_hypervisor_stats(user):
    return (
        Host.objects.get_for_user(user)
        .filter(archived=False)
        .values("hypervisor")
        .annotate(count=Count("hypervisor"))
    )


def get_customer_stats(user):
    return (
        Host.objects.get_for_user(user)
        .filter(archived=False)
        .values("customer")
        .annotate(count=Count("customer"))
    )


def get_alert_stats():
    num_critical = Host.objects.filter(
        alerts__severity=AlertSeverity.CRITICAL,
        alerts__acknowledgement=None,
        archived=False,
    ).count()
    num_warning = (
        Host.objects.filter(
            alerts__severity=AlertSeverity.WARNING,
            alerts__acknowledgement=None,
            archived=False,
        )
        .exclude(
            alerts__severity=AlertSeverity.CRITICAL,
        )
        .count()
    )
    num_info = (
        Host.objects.filter(
            alerts__severity=AlertSeverity.INFO,
            alerts__acknowledgement=None,
            archived=False,
        )
        .exclude(
            alerts__severity__in=[AlertSeverity.WARNING, AlertSeverity.CRITICAL],
        )
        .count()
    )

    # Complicated union
    # The 'basic' case counts all hosts with 0 alerts
    # The 'advanced' case counts all hosts with no unacknowledged alerts
    num_fine = (
        Host.objects.filter(archived=False, alerts__isnull=True)
        # This annotate is needed for the union, as that adds this column
        # The value is bogus and ignored
        .annotate(unacknowledged_alerts=Count("id"))
        .union(
            Host.objects.exclude(alerts__isnull=True)
            .annotate(
                unacknowledged_alerts=Count(
                    "alerts",
                    filter=Q(alerts__acknowledgement=None),
                )
            )
            .filter(unacknowledged_alerts=0, archived=False)
        )
        .count()
    )

    return num_critical, num_warning, num_info, num_fine


def get_alert_count_by_message(user):
    return (
        Alert.objects.get_for_user(user)
        .filter(acknowledgement=None)
        .values("short_message")
        .annotate(count=Count("id"))
    )


def get_host_count_by_otap(user):
    return (
        Host.objects.get_for_user(user)
        .filter(archived=False)
        .values("otap_stage")
        .annotate(count=Count("id"))
    )


def get_hosts_by_datasource(user):
    return (
        Host.objects.get_for_user(user)
        .filter(archived=False)
        .values("data_source__name")
        .annotate(count=Count("id"))
    )


def get_easter_stats():
    # Create a seeded random, with the seed being 'today'
    # This is for consistent bollocks per day
    rn = random.Random(date.today().isoformat())

    gremlins = [
        {"label": "Evil gremlins", "count": rn.randint(0, 100)},
        {"label": "Neutral gremlins", "count": rn.randint(0, 100)},
        {"label": "Good gremlins", "count": rn.randint(0, 10)},
    ]

    top_excuses_for_downtime = [
        {"label": "It worked on my machine", "count": rn.randint(1, 20)},
        {"label": "DNS", "count": rn.randint(20, 30)},
        {"label": "Deployed on a friday", "count": rn.randint(1, 20)},
        {"label": "Aliens", "count": rn.randint(1, 20)},
        {"label": "DC03 is down", "count": rn.randint(1, 15)},
        {"label": "Somehow DNS again", "count": rn.randint(5, 25)},
        {"label": "CentOS", "count": rn.randint(1, 20)},
        {
            "label": "Docker cannot write package requirements",
            "count": rn.randint(1, 20),
        },
    ]

    ducks_per_dc = [
        {"label": "ALM", "count": rn.randint(30, 100)},
        {"label": "UMC", "count": rn.randint(10, 20)},
        {
            "label": "D10",
            "count": 8,
        },  # This one is legit, nobody has found them yet
    ]

    coffee_machine_downtime = [
        {"label": "Monday", "percent": rn.randint(0, 100)},
        {"label": "Tuesday", "percent": rn.randint(0, 100)},
        {"label": "Wednesday", "percent": rn.randint(0, 100)},
        {"label": "Thursday", "percent": rn.randint(0, 100)},
        {"label": "Friday", "percent": rn.randint(0, 100)},
    ]

    productivity = [
        {"label": x["label"], "percent": 100 - x["percent"]}
        for x in coffee_machine_downtime
    ]

    return (
        gremlins,
        top_excuses_for_downtime,
        ducks_per_dc,
        coffee_machine_downtime,
        productivity,
    )
