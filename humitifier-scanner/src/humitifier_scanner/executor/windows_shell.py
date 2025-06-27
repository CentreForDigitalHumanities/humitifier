import json
import shlex
import threading
from base64 import b64encode
from dataclasses import dataclass
from typing import Union

from winrm import Session
from winrm.protocol import Protocol

from humitifier_scanner.config import CONFIG
from humitifier_scanner.executor.shared import (
    LOCAL_HOSTS,
    ShellExecutor,
    LocalShellExecutor,
    ShellOutput,
)
from humitifier_scanner.logger import logger


@dataclass
class JsonShellOutput:
    data: dict | list
    stderr: list[str]
    return_code: int


class PowershellMixin:

    def execute_pwsh(
        self, command: str | list[str], fail_silent: bool = False
    ) -> ShellOutput:
        if isinstance(command, list):
            command = shlex.join(command)

        logger.debug(f"Executing command: {command}")

        # must use utf16 little endian on windows
        encoded_ps = b64encode(command.encode("utf_16_le")).decode("ascii")
        command = "powershell -encodedcommand {0}".format(encoded_ps)
        rs = self.execute(command)

        if len(rs.stderr):
            # Convert stderr to a byte-string and clean it
            stderr = b"\r\n".join(
                [s.encode("utf-8") if isinstance(s, str) else s for s in rs.stderr]
            )

            logger.debug("Parsing stderr: %s", stderr)

            # Create a bogus session, because we want to use it's error-parsing
            bogus_session = Session("https://example.org:999999", ("a", "b"))
            stderr = bogus_session._clean_error_msg(stderr)

            # Return the parsed stuff back to str
            rs.stderr = stderr.decode("utf-8").splitlines()

        return rs

    def execute_pwsh_json(
        self, command: str | list[str], fail_silent: bool = False
    ) -> JsonShellOutput:
        if isinstance(command, list):
            command = shlex.join(command)

        command = f"{command} | ConvertTo-Json"

        result = self.execute_pwsh(command, fail_silent)

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


class LocalWindowsShellExecutor(PowershellMixin, LocalShellExecutor):
    pass


class WinRMPWindowsShellExecutor(PowershellMixin, ShellExecutor):
    ERROR_MSG_NO_WINRM_CONFIG = (
        "Cannot create WinRM shell executor without WinRM config"
    )

    def __init__(self, host: str):
        if CONFIG.winrm is None:
            raise ValueError(self.ERROR_MSG_NO_WINRM_CONFIG)

        self.host = host

        self.protocol: Protocol | None = None
        self._connect()

    ##
    ## Connection logic
    ##

    def _connect(self):
        if CONFIG.winrm.server_cert_validation is False:
            logger.debug("Not using server cert validation")

        self.protocol = Protocol(
            endpoint=f"https://{self.host}:5986/wsman",
            transport=CONFIG.winrm.auth_mechanism,
            username=CONFIG.winrm.user,
            password=CONFIG.winrm.password,
            server_cert_validation=(
                "validate" if CONFIG.winrm.server_cert_validation else "ignore"
            ),
            credssp_disable_tlsv1_2=True,
        )

    def close(self):
        if self.protocol:
            self.protocol.transport.close_session()
        self.protocol = None

    def _reconnect(self):
        self.close()
        self._connect()

    ##
    ## Execution logic
    ##

    def _execute_cmd(self, command: str, arguments: list[str]) -> ShellOutput:
        logger.debug(
            f"Executing command on {self.host}: {command}; arguments: {arguments}"
        )

        # Open a shell and run it
        shell_id = self.protocol.open_shell()
        command_id = self.protocol.run_command(shell_id, command, arguments)

        # Retrieve results
        std_out, std_err, return_code = self.protocol.get_command_output(
            shell_id, command_id
        )

        # Cleanup and close
        self.protocol.cleanup_command(shell_id, command_id)
        self.protocol.close_shell(shell_id)

        # Parse returns
        std_out = std_out.decode("utf-8")
        std_err = std_err.decode("utf-8")

        std_out = std_out.splitlines()
        std_err = std_err.splitlines()

        return ShellOutput(
            stdout=std_out,
            stderr=std_err,
            return_code=return_code,
        )

    def execute(
        self, command: str | list[str], fail_silent: bool = False
    ) -> ShellOutput:
        if isinstance(command, str):
            command = shlex.split(command, posix=False)

        actual_command = command[0]
        arguments = []
        if len(command) > 1:
            arguments = command[1:]

        return self._execute_cmd(actual_command, arguments)


WindowsShellExecutor = Union[LocalWindowsShellExecutor, WinRMPWindowsShellExecutor]


class _ExecutorManager:
    _connections = {}
    _lock = threading.Lock()  # Lock to prevent threading issues

    @classmethod
    def get_executor(cls, host: str):
        # Local hosts aren't cached, as they don't require state
        # management
        if host in LOCAL_HOSTS:
            return LocalWindowsShellExecutor()

        with cls._lock:
            return cls._get_remote_executor(host)

    @classmethod
    def _get_remote_executor(cls, host, retries=3):
        if host not in cls._connections:
            logger.debug(f"Creating new WinRM connection to {host}")
            try:
                cls._connections[host] = WinRMPWindowsShellExecutor(host)
            except Exception as e:
                if retries > 0:
                    logger.debug(
                        f"Failed to create new WinRM connection to {host}: {e}. Retrying... ({retries} left",
                        exc_info=True,
                    )
                    return cls._get_remote_executor(host, retries - 1)

                logger.error(f"Failed to create new WinRM connection to {host}")
                raise e

        connection: WinRMPWindowsShellExecutor = cls._connections[host]

        return cls._connections[host]

    @classmethod
    def close_connection(cls, host):
        if host in LOCAL_HOSTS:
            return

        with cls._lock:
            if host in cls._connections:
                del cls._connections[host]

    @classmethod
    def close_all(cls):
        with cls._lock:
            for ssh in cls._connections.values():
                ssh.close()
            cls._connections.clear()


def get_executor(host: str) -> WindowsShellExecutor:
    logger.debug(f"Getting shell executor for host: {host}")
    return _ExecutorManager.get_executor(host)


def close_connection(host: str):
    logger.debug(f"Closing shell executor for host: {host}")
    _ExecutorManager.close_connection(host)
