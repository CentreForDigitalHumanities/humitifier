from alerting.backend.data import AlertData
from alerting.backend.generator import BaseScanAlertGenerator
from alerting.models import AlertSeverity
from humitifier_common.scan_data import ErrorTypeEnum


class ScanErrorAlertGenerator(BaseScanAlertGenerator):

    verbose_name = "Scan error"

    def generate_alerts(self) -> AlertData | list[AlertData] | None:
        alerts = []
        for error in self.scan_output.errors:
            # Execution errors are not fatal, unless global_error is set
            fatal = (
                error.type is not None and error.type != ErrorTypeEnum.EXECUTION_ERROR
            ) or error.global_error

            err_string = error.message
            if error.artefact:
                err_string = f"Error during collecting {error.artefact}"
                if error.collector_implementation:
                    err_string += f" ({error.collector_implementation})"

            if fatal:
                message = (
                    f"There was a fatal error during the last scan; the scan "
                    f"was rejected as a result. Error: {err_string}"
                )
                severity = AlertSeverity.CRITICAL
            else:
                message = f"There was an error during the last scan: {err_string}"
                severity = AlertSeverity.WARNING

            # This custom identifier will not be displayed, but must be as unique as
            # possible
            custom_identifier = (
                f"{error.artefact}-"
                f"{error.collector_implementation}-"
                f"{error.type}"
            )
            if error.metadata:
                custom_identifier += (
                    f"-{error.metadata.identifier}-{error.metadata.py_exception}"
                )

            alerts.append(
                AlertData(
                    severity=severity,
                    message=message,
                    fatal=fatal,
                    custom_identifier=custom_identifier,
                )
            )

        return alerts
