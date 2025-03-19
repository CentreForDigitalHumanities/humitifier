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
