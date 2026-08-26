from datetime import datetime

from alerting.backend.data import AlertData
from alerting.backend.generator import BaseArtefactAlertGenerator
from alerting.models import AlertSeverity
from humitifier_common.artefacts import *


class PyInfraReportAlertGenerator(BaseArtefactAlertGenerator):

    artefact = PyInfraReport
    verbose_name = "PyInfra"

    def generate_alerts(self) -> AlertData | list[AlertData] | None:
        alerts = []

        if self.artefact_data.success is False:
            alerts.append(
                AlertData(
                    severity=AlertSeverity.CRITICAL,
                    message="PyInfra runs are failing!",
                    custom_identifier="failing",
                )
            )

        if last_run := self.artefact_data.start_time:
            try:
                last_run = datetime.fromisoformat(last_run)
            except ValueError:
                last_run = datetime.now()

            diff = self.scan_date - last_run
            if diff.total_seconds() > (60 * 60 * 24 * 7):
                alerts.append(
                    AlertData(
                        severity=AlertSeverity.WARNING,
                        message=f"PyInfra hasn't run in (over) 1 week ({diff})",
                        custom_identifier="run_too_long_ago",
                    )
                )

        return alerts
