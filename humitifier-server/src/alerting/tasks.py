from celery import shared_task
from django.utils import timezone

from hosts.models import Host
from humitifier_common.scan_data import ScanOutput
from humitifier_server.celery.task_names import (
    ALERTING_GENERATE_ALERTS,
    ALERTING_SAVE_ALERTS,
)
from humitifier_server.logger import logger

from .backend.data import AnnotatedAlertData, GeneratedAlerts
from .backend.registry import alert_generator_registry
from .models import Alert


@shared_task(name=ALERTING_GENERATE_ALERTS, pydantic=True)
def generate_alerts(scan_output: ScanOutput) -> ScanOutput | None:
    """Main task for generating alerts for a given ScanOutput."""
    try:
        host = Host.objects.get(fqdn=scan_output.hostname)
    except Host.DoesNotExist as e:
        logger.error(f"Host {scan_output.hostname} is not found")
        raise e

    # Accumulate all alerts from both stages
    all_alerts = []

    # Step 1: Process scan-based alerts
    scan_alerts, scan_fatal_found = _process_alert_generators(
        host,
        alert_generator_registry.get_scan_alert_generators(scan_output),
        stop_on_fatal=True,
    )
    all_alerts.extend(scan_alerts)
    if scan_fatal_found:
        _save_alerts_to_task(host.fqdn, all_alerts)
        return None

    # Step 2: Process artefact-based alerts (only if no fatal alerts from step 1)
    artefact_alerts, artefact_fatal_found = _process_alert_generators(
        host,
        alert_generator_registry.get_artefact_alert_generators(scan_output),
        stop_on_fatal=False,
    )
    all_alerts.extend(artefact_alerts)

    # Save all accumulated alerts once (fatal + non-fatal from all stages)
    _save_alerts_to_task(host.fqdn, all_alerts)

    # Stop further processing if any fatal alert was found
    if artefact_fatal_found:
        return None

    # No fatal alerts found, return the scan_output for further processing
    return scan_output


def _process_alert_generators(
    host, generators, stop_on_fatal
) -> tuple[list[AnnotatedAlertData], bool]:
    alerts = []
    fatal_found = False

    for generator in generators:
        existing_alerts = host.alerts.filter(_creator=generator._creator)
        generated_alerts = generator.run(existing_alerts)

        if not generated_alerts:
            continue

        alerts.extend(generated_alerts)

        # Separate fatal and non-fatal alerts
        fatal_alerts = [alert for alert in generated_alerts if alert.data.fatal]

        if fatal_alerts:
            fatal_found = True
            if stop_on_fatal:
                return alerts, fatal_found

    return alerts, fatal_found


def _save_alerts_to_task(host_fqdn, alerts):
    """
    Save all alerts for a given host by sending them to the save_alerts task.
    """
    logger.info(f"Saving {len(alerts)} alerts for host {host_fqdn}.")
    save_alerts.delay(
        GeneratedAlerts(host=host_fqdn, alerts=alerts).model_dump(mode="json")
    )


@shared_task(name=ALERTING_SAVE_ALERTS, pydantic=True)
def save_alerts(generated_alerts: GeneratedAlerts):
    try:
        host = Host.objects.get(fqdn=generated_alerts.host)
    except Host.DoesNotExist as e:
        logger.error(f"Start-scan: Host {generated_alerts.host} is not found")
        raise e

    current_ids = []

    for generated_alert in generated_alerts.alerts:
        if generated_alert.existing:
            alert_obj = host.alerts.get(
                _creator=generated_alert.creator,
                custom_identifier=generated_alert.data.custom_identifier,
            )
        else:
            alert_obj = Alert()
            alert_obj._creator = generated_alert.creator
            alert_obj.custom_identifier = generated_alert.data.custom_identifier
            alert_obj.host = host

        alert_obj.last_seen_at = timezone.now()
        alert_obj._notified = False

        alert_obj.short_message = generated_alert.creator_verbose_name
        alert_obj.message = generated_alert.data.message
        alert_obj.severity = generated_alert.data.severity
        alert_obj._can_acknowledge = generated_alert.data.can_acknowledge

        alert_obj.save()

        current_ids.append(alert_obj.id)

    host.alerts.exclude(id__in=current_ids).delete()
