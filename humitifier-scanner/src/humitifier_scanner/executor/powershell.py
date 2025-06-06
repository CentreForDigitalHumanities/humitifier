import json
import shlex
from dataclasses import dataclass
from typing import Union

from humitifier_scanner.executor.shared import LocalShellExecutor, ShellOutput
from humitifier_scanner.logger import logger


@dataclass
class JsonShellOutput:
    data: dict | list
    stderr: list[str]
    return_code: int

class PowershellMixin:

    def execute(self, command: str | list[str], fail_silent: bool = False) -> ShellOutput:
        if isinstance(command, list):
            command = shlex.join(command)

        command = ["powershell", "-c", command]

        return super().execute(command, fail_silent)

    def execute_json(self, command: str | list[str], fail_silent: bool = False) -> JsonShellOutput:
        if isinstance(command, list):
            command = shlex.join(command)

        command = f"{command} | ConvertTo-Json"

        result = self.execute(command, fail_silent)

        json_data = {}
        if result.stdout:
            data = "".join(result.stdout)
            try:
                json_data = json.loads(data)
            except ValueError:
                pass

        return JsonShellOutput(
            data=json_data,
            stderr=result.stderr,
            return_code=result.return_code,
        )




class LocalPowershellExecutor(PowershellMixin, LocalShellExecutor):
    pass


PowershellExecutor = Union[LocalPowershellExecutor]


def get_executor(host: str) -> LocalPowershellExecutor:
    logger.debug(f"Getting shell executor for host: {host}")
    return LocalPowershellExecutor()


def close_connection(host: str):
    logger.debug(f"Closing shell executor for host: {host}")

