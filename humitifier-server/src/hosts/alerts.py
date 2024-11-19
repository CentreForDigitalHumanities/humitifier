from hosts.models import AlertLevel, AlertType, Host


def outdated_os(scan_data: dict, host: Host):
    """The OS is outdated"""
    hostname_ctl_data = scan_data.get("HostnameCtl", None)

    OUTDATED_OS = [
        "Debian GNU/Linux 10 (buster)",
        "Debian GNU/Linux 9 (stretch)",
        "CentOS Linux 7 (Core)",
    ]

    if not hostname_ctl_data or not isinstance(hostname_ctl_data, dict):
        return None

    if os := hostname_ctl_data.get("os"):
        if os in OUTDATED_OS:
            return host.alerts.get_or_create(
                level=AlertLevel.WARNING,
                type=AlertType.OUTDATED_OS,
                message="The operating system is no longer supported",
            )


def has_fact_error(scan_data, host):
    """One or more facts could not be collected"""

    for fact, data in scan_data.items():
        if not isinstance(data, dict):
            # Some facts are not dicts if they succeeded, so we can assume it
            # was fine
            continue

        if "exception" in data:
            return host.alerts.get_or_create(
                level=AlertLevel.CRITICAL,
                type=AlertType.FACT_ERROR,
                message="One or more facts could not be collected",
            )


def puppet_agent_disabled(scan_data: dict, host: Host):
    """Puppet agent is disabled"""
    puppet_agent_status = scan_data.get("PuppetAgentStatus")

    if not puppet_agent_status or not isinstance(puppet_agent_status, dict):
        return None

    if puppet_agent_status.get("disabled"):

        return host.alerts.get_or_create(
            level=AlertLevel.CRITICAL,
            type=AlertType.DISABLED_PUPPET,
            message="Puppet agent is disabled",
        )


ALERTS = [outdated_os, has_fact_error, puppet_agent_disabled]


def generate_alerts(scan_data: dict, host: Host, delete_old_alerts: bool = True):
    alerts = []

    if host.archived:
        return alerts

    if not scan_data:
        return host.alerts.get_or_create(
            level=AlertLevel.CRITICAL,
            type="no_scan_data",
            message="No scan data available",
        )
    else:
        for alert_func in ALERTS:
            if alert_data := alert_func(scan_data, host):
                alert, created = alert_data
                alerts.append(alert)

    if delete_old_alerts:
        host.alerts.exclude(pk__in=[alert.pk for alert in alerts]).delete()

    return alerts
