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
    try:
        # Attempt to fetch the host based on the FQDN. Log an error if the host does not exist.
        host = Host.objects.get(fqdn=scan_output.hostname)
    except Host.DoesNotExist as e:
        logger.error(f"Start-scan: Host {scan_output.hostname} is not found")
        raise e

    alerts: list[AnnotatedAlertData] = []

    scan_alert_generators = alert_generator_registry.get_scan_alert_generators(
        scan_output
    )
    for generator in scan_alert_generators:
        existing_alerts = host.alerts.filter(_creator=generator._creator)
        generated_alerts = generator.run(existing_alerts)
        if generated_alerts:
            alerts += generated_alerts

    fatal_alerts = [alert for alert in alerts if alert.data.fatal]

    if fatal_alerts:
        save_alerts.delay(
            GeneratedAlerts(host=host.fqdn, alerts=fatal_alerts).model_dump(mode="json")
        )
        return None

    artefact_alert_generators = alert_generator_registry.get_artefact_alert_generators(
        scan_output
    )
    for generator in artefact_alert_generators:
        existing_alerts = host.alerts.filter(_creator=generator._creator)
        generated_alerts = generator.run(existing_alerts)
        if generated_alerts:
            alerts += generated_alerts

    fatal_alerts = [alert for alert in alerts if alert.data.fatal]

    if fatal_alerts:
        save_alerts.delay(
            GeneratedAlerts(host=host.fqdn, alerts=fatal_alerts).model_dump(mode="json")
        )
        return None

    save_alerts.delay(
        GeneratedAlerts(host=host.fqdn, alerts=alerts).model_dump(mode="json")
    )

    # Return scan output for further processing
    return scan_output


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
