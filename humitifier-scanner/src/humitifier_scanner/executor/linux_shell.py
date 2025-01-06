import abc
import platform
import threading
from dataclasses import dataclass

import paramiko
from paramiko.channel import ChannelFile, ChannelStderrFile, ChannelStdinFile

from humitifier_scanner.config import CONFIG
from humitifier_scanner.logger import logger

LOCAL_HOSTS = ["localhost", "127.0.0.1", "::1", platform.node()]


@dataclass
class ShellOutput:
    stdout: list[str]
    stderr: list[str]
    return_code: int


class LinuxShellExecutor(abc.ABC):

    @abc.abstractmethod
    def execute(self, command: str, fail_silent: bool = False) -> ShellOutput:
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

    @staticmethod
    def get(host: str) -> "LinuxShellExecutor":
        if host in LOCAL_HOSTS:
            return LocalLinuxShellExecutor()

        return RemoteLinuxShellExecutor(host)


class LocalLinuxShellExecutor(LinuxShellExecutor):

    def execute(self, command: str, fail_silent: bool = False) -> ShellOutput:
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
            log_cmd(f"Command failed with return code {process.returncode}")

        return ShellOutput(
            stdout_lines,
            stderr_lines,
            process.returncode,
        )


class RemoteLinuxShellExecutor(LinuxShellExecutor):

    def __init__(self, host: str):
        if CONFIG.ssh is None:
            raise ValueError("Cannot create SSH shell executor without SSH config")

        #
        # Setup primary SSH client
        #
        self.host = host

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.ssh_user = CONFIG.ssh.user

        pkey_password = None
        if CONFIG.ssh.private_key_password:
            pkey_password = CONFIG.ssh.private_key_password.get_secret_value()

        with open(CONFIG.ssh.private_key, "r") as f:
            self.private_key = paramiko.Ed25519Key(file_obj=f, password=pkey_password)

        #
        # Handle bastion host, if configured
        #
        self.bastion_enabled = CONFIG.ssh.bastion is not None
        if not self.bastion_enabled:
            return

        logger.debug(f"Configuring bastion host for {host}")

        self.bastion_host = CONFIG.ssh.bastion.host

        if CONFIG.ssh.bastion.private_key:
            bastion_pkey_password = None
            if CONFIG.ssh.bastion.private_key_password:
                bastion_pkey_password = (
                    CONFIG.ssh.bastion.private_key_password.get_secret_value()
                )

            with open(CONFIG.ssh.bastion.private_key, "r") as f:
                self.bastion_private_key = paramiko.Ed25519Key(
                    file_obj=f, password=bastion_pkey_password
                )
        else:
            self.bastion_private_key = self.private_key
        self.bastion_user = CONFIG.ssh.bastion.user or self.ssh_user

        self.bastion_client = paramiko.SSHClient()
        self.bastion_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def _connect(self):
        if not self.ssh_client.get_transport():

            connection_kwargs = {
                "hostname": self.host,
                "username": self.ssh_user,
                "pkey": self.private_key,
            }

            # If we have a bastion host, we need some more setup
            if self.bastion_enabled:
                logger.debug(
                    f"Connecting SSH client for bastion host {self.bastion_host}"
                )
                self.bastion_client.connect(
                    self.bastion_host,
                    username=self.bastion_user,
                    pkey=self.bastion_private_key,
                )

                bastion_transport = self.bastion_client.get_transport()
                bastion_channel = bastion_transport.open_channel(
                    "direct-tcpip", (self.host, 22), ("", 0)
                )

                connection_kwargs["sock"] = bastion_channel

            logger.debug(f"Connecting SSH client for host {self.host}")
            self.ssh_client.connect(**connection_kwargs)

    def _execute_command(
        self, command: str, fail_silent: bool = False
    ) -> tuple[ChannelStdinFile, ChannelFile, ChannelStderrFile]:
        self._connect()
        logger.debug(f"Executing command on {self.host}: {command}")
        stdin, stdout, stderr = self.ssh_client.exec_command(command)

        if stdout.channel.recv_exit_status() != 0:
            log_cmd = logger.debug if fail_silent else logger.error
            log_cmd(
                f"Command failed with return code {stdout.channel.recv_exit_status()}. Stderr: {stderr.read().decode()}"
            )

        return stdin, stdout, stderr

    def execute(self, command: str, fail_silent: bool = False) -> ShellOutput:
        stdin, stdout, stderr = self._execute_command(command, fail_silent)

        # Strip empty lines
        stdout_lines = [
            line for line in stdout.read().decode().split("\n") if line.strip()
        ]
        stderr_lines = [
            line for line in stderr.read().decode().split("\n") if line.strip()
        ]

        return ShellOutput(
            stdout_lines,
            stderr_lines,
            stdout.channel.recv_exit_status(),
        )

    def close(self):
        self.ssh_client.close()
        if self.bastion_enabled:
            self.bastion_client.close()


class _ExecutorManager:
    _connections = {}
    _lock = threading.Lock()  # Lock to prevent threading issues

    @classmethod
    def get_executor(cls, host: str):
        # Local hosts aren't cached, as they don't require state
        # management
        if host in LOCAL_HOSTS:
            return LocalLinuxShellExecutor()

        with cls._lock:
            if (
                host not in cls._connections
                or not cls._connections[host].ssh_client.get_transport().is_active()
            ):
                logger.debug(f"Creating new SSH connection to {host}")
                cls._connections[host] = RemoteLinuxShellExecutor(host)

            return cls._connections[host]

    @classmethod
    def close_connection(cls, host):
        if host in LOCAL_HOSTS:
            return

        with cls._lock:
            if host in cls._connections:
                logger.debug(f"Closing SSH connection to {host}")
                cls._connections[host].close()
                del cls._connections[host]

    @classmethod
    def close_all(cls):
        with cls._lock:
            for ssh in cls._connections.values():
                ssh.close()
            cls._connections.clear()


def get_executor(host: str) -> LinuxShellExecutor:
    logger.debug(f"Getting shell executor for host: {host}")
    return _ExecutorManager.get_executor(host)


def close_connection(host: str):
    logger.debug(f"Closing shell executor for host: {host}")
    _ExecutorManager.close_connection(host)
