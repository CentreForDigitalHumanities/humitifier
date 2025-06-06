import abc
from dataclasses import dataclass

from humitifier_scanner.logger import logger
from humitifier_scanner.utils import get_local_fqdn

LOCAL_HOSTS = ["localhost", "127.0.0.1", "::1", get_local_fqdn()]

@dataclass
class ShellOutput:
    stdout: list[str]
    stderr: list[str]
    return_code: int


class ShellExecutor(abc.ABC):

    @abc.abstractmethod
    def execute(
        self, command: str | list[str], fail_silent: bool = False
    ) -> ShellOutput:
        """
        Provides an abstract method for executing a command in a shell-like environment and obtaining its
        output as a `ShellOutput` object. The method must be implemented by subclasses and allows handling
        of execution failures optionally in a silent manner.

        :param command: The shell command to execute.
        :type command: str
        :param fail_silent: Determines whether the method suppresses errors during command
            execution. Defaults to False.
        :type fail_silent: bool
        :return: The output of the executed shell command encapsulated in a `ShellOutput` object.
        :rtype: ShellOutput
        """
        pass


class LocalShellExecutor(ShellExecutor):

    def execute(
        self, command: str | list[str], fail_silent: bool = False
    ) -> ShellOutput:
        import subprocess

        logger.debug(f"Executing command locally: {command}")

        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()

        # Strip empty lines
        stdout_lines = [line.decode() for line in stdout.splitlines() if line.strip()]
        stderr_lines = [line.decode() for line in stderr.splitlines() if line.strip()]

        if process.returncode != 0:
            log_cmd = logger.debug if fail_silent else logger.error
            log_cmd(f"Command '{command}' failed with return code {process.returncode}")

        return ShellOutput(
            stdout_lines,
            stderr_lines,
            process.returncode,
        )
