import abc
import platform
import threading
from dataclasses import dataclass
from pathlib import Path
from subprocess import list2cmdline
from typing import Literal, TextIO

import paramiko
from paramiko import SFTPClient, SFTPFile

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

    def open_file(
        self, filename: str | Path, mode: Literal["r", "rb", "rt"] = "r"
    ) -> TextIO | SFTPFile:
        if not isinstance(filename, Path):
            filename = Path(filename)

        if not filename.is_absolute():
            raise ValueError("Filename must be a absolute path")

        if mode not in ["r", "rb", "rt"]:
            raise ValueError("Mode must be 'r' or 'rb'")

        logger.debug(f"Opening file {filename}")

        return self._open_file(filename, mode)

    @abc.abstractmethod
    def _open_file(self, filename: Path, mode: str) -> TextIO | SFTPFile:
        pass

    @staticmethod
    def get(host: str) -> "LinuxShellExecutor":
        if host in LOCAL_HOSTS:
            return LocalLinuxShellExecutor()

        return RemoteLinuxShellExecutor(host)


class LocalLinuxShellExecutor(LinuxShellExecutor):

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

    def _open_file(self, filename: Path, mode: str) -> TextIO:
        if mode not in ["r", "rb", "rt"]:
            raise ValueError("Mode must be 'r' or 'rb'")

        return open(filename, mode)


class RemoteLinuxShellExecutor(LinuxShellExecutor):
    DEFAULT_SSH_PORT = 22
    ERROR_MSG_NO_SSH_CONFIG = "Cannot create SSH shell executor without SSH config"
    TIMEOUT = 30

    def __init__(self, host: str):
        if CONFIG.ssh is None:
            raise ValueError(self.ERROR_MSG_NO_SSH_CONFIG)

        self.host, self.port = self._extract_host_port(host)
        self.ssh_user = CONFIG.ssh.user
        self.private_key = self._load_private_key(
            CONFIG.ssh.private_key, CONFIG.ssh.private_key_password
        )

        self.ssh_client = self._get_ssh_client()
        self.sftp_client: SFTPClient | None = None

        self.bastion_enabled = CONFIG.ssh.bastion is not None

        self._connect()

    #
    # Helpers
    #

    @staticmethod
    def _get_ssh_client() -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return client

    @staticmethod
    def _load_private_key(private_key_path: str, private_key_password):
        password = (
            private_key_password.get_secret_value() if private_key_password else None
        )
        with open(private_key_path, "r") as f:
            return paramiko.Ed25519Key(file_obj=f, password=password)

    def _extract_host_port(self, host: str):
        host, _, port = host.partition(":")
        return host, int(port) if port else self.DEFAULT_SSH_PORT

    def _get_default_connection_kwargs(self):
        return {
            "timeout": self.TIMEOUT,
            "banner_timeout": self.TIMEOUT,
            "auth_timeout": self.TIMEOUT,
            "channel_timeout": self.TIMEOUT,
        }

    #
    # Connection handling
    #

    def _configure_bastion(self):
        logger.debug(f"Configuring bastion host for {self.host}")
        self.bastion_host, self.bastion_port = self._extract_host_port(
            CONFIG.ssh.bastion.host
        )

        self.bastion_private_key = (
            self._load_private_key(
                CONFIG.ssh.bastion.private_key, CONFIG.ssh.bastion.private_key_password
            )
            if CONFIG.ssh.bastion.private_key
            else self.private_key
        )

        self.bastion_user = CONFIG.ssh.bastion.user or self.ssh_user
        self.bastion_client = self._get_ssh_client()

    def _connect(self):
        if self.ssh_client.get_transport():
            return

        connection_params = self._get_default_connection_kwargs()
        connection_params.update(
            {
                "hostname": self.host,
                "username": self.ssh_user,
                "pkey": self.private_key,
                "port": self.port,
            }
        )

        if self.bastion_enabled:
            logger.debug(f"Setting up bastion transport for host {self.host}")
            connection_params["sock"] = self._setup_bastion_transport()

        logger.debug(f"Connecting to SSH client for host {self.host}")
        self.ssh_client.connect(**connection_params)

    def _setup_bastion_transport(self):
        self._configure_bastion()

        self.bastion_client.connect(
            hostname=self.bastion_host,
            username=self.bastion_user,
            pkey=self.bastion_private_key,
            port=self.bastion_port,
            **self._get_default_connection_kwargs(),
        )
        bastion_transport = self.bastion_client.get_transport()

        return bastion_transport.open_channel(
            "direct-tcpip", (self.host, self.port), ("", 0)
        )

    def close(self):
        if self.sftp_client:
            self.sftp_client.close()
        self.ssh_client.close()
        if self.bastion_enabled:
            self.bastion_client.close()

    #
    # Execution
    #

    def _execute_command(self, command: str, fail_silent: bool = False):
        logger.debug(f"Executing command on {self.host}: {command}")
        stdin, stdout, stderr = self.ssh_client.exec_command(command)

        if stdout.channel.recv_exit_status() != 0:
            log_cmd = logger.debug if fail_silent else logger.error
            log_cmd(
                f"Command '{command}' failed with return code {stdout.channel.recv_exit_status()}."
                f" Stderr: {stderr.read().decode()}"
            )

        return stdin, stdout, stderr

    def execute(
        self, command: str | list[str], fail_silent: bool = False
    ) -> ShellOutput:
        if isinstance(command, list):
            command = list2cmdline(command)
        stdin, stdout, stderr = self._execute_command(command, fail_silent)

        # Strip empty lines
        stdout_lines = [
            line for line in stdout.read().decode().split("\n") if line.strip()
        ]
        stderr_lines = [
            line for line in stderr.read().decode().split("\n") if line.strip()
        ]

        return ShellOutput(
            stdout_lines, stderr_lines, stdout.channel.recv_exit_status()
        )

    def _open_file(self, filename: Path, mode: str) -> SFTPFile:
        if mode not in ["r", "rb", "rt"]:
            raise ValueError("Mode must be 'r' or 'rb'")

        if self.sftp_client is None:
            logger.debug(f"Creating SFTP client for host {self.host}")
            self.sftp_client = self.ssh_client.open_sftp()

        return self.sftp_client.open(str(filename), mode)

    #
    # Magic
    #

    def __repr__(self):
        return f"<RemoteLinuxShellExecutor(host={self.host}, port={self.port})>"

    def __del__(self):
        logger.debug(f"Closing ssh connection to {self.host}")
        self.close()


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
            return cls._get_remote_executor(host)

    @classmethod
    def _get_remote_executor(cls, host, retries=3):
        if host not in cls._connections:
            logger.debug(f"Creating new SSH connection to {host}")
            try:
                cls._connections[host] = RemoteLinuxShellExecutor(host)
            except Exception as e:
                if retries > 0:
                    logger.debug(
                        f"Failed to create new SSH connection to {host}: {e}. Retrying... ({retries} left",
                        exc_info=True,
                    )
                    return cls._get_remote_executor(host, retries - 1)

                logger.error(f"Failed to create new SSH connection to {host}")
                raise e

        connection: RemoteLinuxShellExecutor = cls._connections[host]

        # Check if the connection is still live
        # Using an actual packet, as is_active() returns false positives
        try:
            transport = connection.ssh_client.get_transport()
            transport.send_ignore()
        except Exception as e:
            del cls._connections[host]
            return cls._get_remote_executor(host, retries)

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


def get_executor(host: str) -> LinuxShellExecutor:
    logger.debug(f"Getting shell executor for host: {host}")
    return _ExecutorManager.get_executor(host)


def close_connection(host: str):
    logger.debug(f"Closing shell executor for host: {host}")
    _ExecutorManager.close_connection(host)
