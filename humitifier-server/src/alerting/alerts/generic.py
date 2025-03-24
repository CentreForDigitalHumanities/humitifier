from alerting.backend.data import AlertData
from alerting.backend.generator import BaseArtefactAlertGenerator
from alerting.models import AlertSeverity
from humitifier_common.artefacts import *


class UptimeAlertGenerator(BaseArtefactAlertGenerator):

    artefact = Uptime
    verbose_name = "Uptime warning"

    THREE_MONTHS_IN_SECONDS = 60 * 60 * 24 * 92
    SIX_MONTHS_IN_SECONDS = 60 * 60 * 24 * 30.25 * 6
    ONE_YEAR_IN_SECONDS = 60 * 60 * 24 * 365

    def generate_alerts(self) -> AlertData | list[AlertData] | None:

        uptime: float = self.artefact_data

        if uptime is None:
            return None

        alert = AlertData(severity=AlertSeverity.INFO, message="blaat")

        if uptime > self.ONE_YEAR_IN_SECONDS:
            alert.severity = AlertSeverity.CRITICAL
            alert.message = "Host has not been rebooted in (over) 1 year"
        elif uptime > self.SIX_MONTHS_IN_SECONDS:
            alert.severity = AlertSeverity.WARNING
            alert.message = "Host has not been rebooted in (over) 6 months"
        elif uptime > self.THREE_MONTHS_IN_SECONDS:
            alert.message = "Host has not been rebooted in (over) 3 months"
        else:
            return None

        return alert


class MemoryAlertGenerator(BaseArtefactAlertGenerator):
    artefact = Memory
    verbose_name = "Memory warning"

    # Ordering is important here, criticals should go first, etc
    # First number is mem threshold, the second is swap; both will need to be
    # exceeded for an alert to be created with the given severity.
    THRESHOLDS = {
        (90, 70): AlertSeverity.CRITICAL,
        (80, 40): AlertSeverity.WARNING,
        (70, 30): AlertSeverity.INFO,
    }

    def generate_alerts(self) -> AlertData | list[AlertData] | None:
        if not self.artefact_data:
            return None

        percent_mem = self.artefact_data.used_mb / self.artefact_data.total_mb * 100
        percent_swap = (
            self.artefact_data.swap_used_mb / self.artefact_data.swap_total_mb * 100
        )

        for threshold, severity in self.THRESHOLDS.items():
            mem_threshold, swap_threshold = threshold
            if percent_mem > mem_threshold and percent_swap > swap_threshold:
                return AlertData(
                    severity=severity,
                    message=f"Memory usage is {percent_mem:.1f}% (threshold: {mem_threshold}%) and Swap usage is {percent_swap:.1f}% (threshold: {swap_threshold}%)",
                )

        return None


class OutdatedOSAlertGenerator(BaseArtefactAlertGenerator):
    artefact = HostnameCtl
    verbose_name = "Outdated OS"

    OUTDATED_OSes = [
        "Debian GNU/Linux 10 (buster)",
        "Debian GNU/Linux 9 (stretch)",
        "CentOS Linux 7 (Core)",
    ]

    def generate_alerts(self) -> AlertData | list[AlertData] | None:
        if not self.artefact_data:
            return None

        if self.artefact_data.os in self.OUTDATED_OSes:
            return AlertData(
                severity=AlertSeverity.INFO,
                message="This operating system is no longer supported",
            )


class BlockDeviceUsageAlertGenerator(BaseArtefactAlertGenerator):
    artefact = Blocks
    verbose_name = "Disk usage"

    CRITICAL_USAGE_THRESHOLD = 90  # percentage
    WARNING_USAGE_THRESHOLD = 80  # percentage

    def generate_alerts(self) -> AlertData | list[AlertData] | None:
        if not self.artefact_data:
            return None

        blocks: Blocks = self.artefact_data
        alerts: list[AlertData] = []

        for block_device in blocks:
            if block_device.use_percent > self.CRITICAL_USAGE_THRESHOLD:
                alerts.append(
                    AlertData(
                        severity=AlertSeverity.CRITICAL,
                        message=f"Disk '{block_device.name}' usage exceeds {self.CRITICAL_USAGE_THRESHOLD}%",
                        custom_identifier=block_device.name,
                    )
                )
            elif block_device.use_percent > self.WARNING_USAGE_THRESHOLD:
                alerts.append(
                    AlertData(
                        severity=AlertSeverity.WARNING,
                        message=f"Disk '{block_device.name}' usage exceeds {self.WARNING_USAGE_THRESHOLD}%",
                        custom_identifier=block_device.name,
                    )
                )

        return alerts


class HarwareAlertGenerator(BaseArtefactAlertGenerator):
    artefact = Hardware
    verbose_name = "Hardware config"

    def generate_alerts(self) -> AlertData | list[AlertData] | None:
        if not self.artefact_data:
            return None

        data: Hardware = self.artefact_data
        alerts = []

        for memrange in data.memory:
            if memrange.state == "offline":
                alerts.append(
                    AlertData(
                        severity=AlertSeverity.CRITICAL,
                        message=f"Memory range {memrange.range} is offline",
                        custom_identifier=f"range-offline-{memrange.range}",
                    )
                )

        return alerts
