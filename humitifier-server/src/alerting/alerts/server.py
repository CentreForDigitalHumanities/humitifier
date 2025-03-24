from datetime import datetime

from alerting.backend.data import AlertData
from alerting.backend.generator import BaseArtefactAlertGenerator
from alerting.models import AlertSeverity
from humitifier_common.artefacts import *


class PuppetAgentAlertGenerator(BaseArtefactAlertGenerator):

    artefact = PuppetAgent
    verbose_name = "Puppet"

    def generate_alerts(self) -> AlertData | list[AlertData] | None:

        if self.artefact_data is None or self.artefact_data.running is None:
            return AlertData(
                severity=AlertSeverity.WARNING,
                message="Puppet agent status is unknown",
                custom_identifier="unkown_status",
            )

        alerts = []

        if self.artefact_data.running is False:
            alerts.append(
                AlertData(
                    severity=AlertSeverity.CRITICAL,
                    message="Puppet agent service is not running!",
                    custom_identifier="not_running",
                )
            )

        if self.artefact_data.enabled is False:
            message = "Puppet agent is disabled."
            if self.artefact_data.disabled_message:
                message += f" Reason: {self.artefact_data.disabled_message}"
            alerts.append(
                AlertData(
                    # We're not going to throw tantrums for this
                    # We're also checking the last run, which errors with a higher
                    # severity
                    severity=AlertSeverity.INFO,
                    message=message,
                    custom_identifier="disabled",
                )
            )

        if self.artefact_data.is_failing:
            alerts.append(
                AlertData(
                    severity=AlertSeverity.CRITICAL,
                    message="Puppet runs are failing!",
                    custom_identifier="failing",
                )
            )

        if last_run := self.artefact_data.last_run:
            try:
                last_run = datetime.fromisoformat(last_run)
            except ValueError:
                last_run = datetime.now()

            diff = self.scan_date - last_run
            if diff.total_seconds() > (60 * 60 * 20):
                alerts.append(
                    AlertData(
                        severity=AlertSeverity.WARNING,
                        message=f"Puppet hasn't run in (over) 20 hours ({diff})",
                        custom_identifier="run_too_long_ago",
                    )
                )

        return alerts
