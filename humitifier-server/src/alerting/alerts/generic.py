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
