import json

from humitifier_common.artefacts import PyInfraReport, PyInfraReportOperation
from humitifier_scanner.collectors import CollectInfo, FileCollector
from humitifier_scanner.executor.linux_files import LinuxFilesExecutor


class PyInfraReportCollector(FileCollector):
    fact = PyInfraReport

    FILE_PATH = "/var/log/pyinfra/run_report.json"

    def collect_from_files(
        self, files_executor: LinuxFilesExecutor, info: CollectInfo
    ) -> PyInfraReport | None:

        try:
            with files_executor.open(self.FILE_PATH) as file:
                data = json.load(file)
                report = PyInfraReport(**data)

                # Only collect the operations that failed, no sense collecting successful ones
                # which only take up space.
                report.failed_operations = [
                    PyInfraReportOperation(**operation)
                    for operation in data["operations"]
                    if operation["error"]
                ]

                return report
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            return None
