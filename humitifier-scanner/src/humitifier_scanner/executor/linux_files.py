import abc
import stat
import threading
from pathlib import Path
from typing import Literal, TextIO

from paramiko import SFTPClient, SFTPFile

from humitifier_scanner.logger import logger

from .shared import LOCAL_HOSTS

from .linux_shell import (
    RemoteLinuxShellExecutor,
    get_executor as get_linux_shell_executor,
)


class LinuxFilesExecutor(abc.ABC):

    def open(
        self, filename: str | Path, mode: Literal["r", "rb", "rt"] = "r"
    ) -> TextIO | SFTPFile:
        logger.debug(f"Opening file {filename}")

        if not isinstance(filename, Path):
            filename = Path(filename)

        if not filename.is_absolute():
            logger.error(f"File {filename} is not a absolute path")
            raise ValueError("Filename must be a absolute path")

        if mode not in ["r", "rb", "rt"]:
            logger.error(f"Mode {mode} is not supported")
            raise ValueError("Mode must be 'r' or 'rb'")

        try:
            return self._open(filename, mode)
        except FileNotFoundError as e:
            logger.error(f"File {filename} not found: {e}")
            raise e

    def list_dir(
        self, dirpath: str | Path, what: Literal["files", "dirs", "both"] = "files"
    ) -> list[Path]:
        if not isinstance(dirpath, Path):
            dirpath = Path(dirpath)

        if not dirpath.is_absolute():
            logger.error(f"Directory {dirpath} is not a absolute path")
            raise ValueError("Filename must be a absolute path")

        logger.debug(f"Listing directory {dirpath}")

        return self._list_dir(dirpath, what)

    @abc.abstractmethod
    def _open(self, filename: Path, mode: str) -> TextIO | SFTPFile:
        pass

    @abc.abstractmethod
    def _list_dir(
        self, dirpath: Path, what: Literal["files", "dirs", "both"]
    ) -> list[Path]:
        pass


class LocalLinuxFilesExecutor(LinuxFilesExecutor):

    def _open(self, filename: Path, mode: str) -> TextIO:
        if mode not in ["r", "rb", "rt"]:
            raise ValueError("Mode must be 'r' or 'rb'")

        return open(filename, mode)

    def _list_dir(
        self, dirpath: Path, what: Literal["files", "dirs", "both"]
    ) -> list[Path]:
        if dirpath.is_file():
            return [dirpath]
        try:
            items = dirpath.iterdir()  # Get all items in the directory
            if what == "files":
                files = [item for item in items if item.is_file()]
            elif what == "dirs":
                files = [item for item in items if item.is_dir()]
            elif what == "both":
                files = list(items)
            else:
                raise ValueError(
                    "Invalid 'what' parameter: must be 'files', 'dirs', or 'both'"
                )

            return [dirpath / file for file in files]
        except Exception as e:
            logger.error(f"Failed to list directory {dirpath}: {e}")
            raise


class RemoteLinuxFilesExecutor(LinuxFilesExecutor):

    def __init__(self, shell_executor: RemoteLinuxShellExecutor):
        super().__init__()
        self.shell_executor = shell_executor
        self.sftp_client: SFTPClient = shell_executor.ssh_client.open_sftp()

    def _open(self, filename: Path, mode: str) -> SFTPFile:
        if mode not in ["r", "rb", "rt"]:
            raise ValueError("Mode must be 'r' or 'rb'")

        return self.sftp_client.open(str(filename), mode)

    def _list_dir(
        self, dirpath: Path, what: Literal["files", "dirs", "both"]
    ) -> list[Path]:
        items = []

        for item in self.sftp_client.listdir_attr(str(dirpath)):
            stat_to_eval = item

            # If we found a symbolic link, we need to follow it
            if stat.S_ISLNK(item.st_mode):
                # Normalize always gives a full absolute path, which is better
                # than `readlink`
                target = self.sftp_client.normalize(str(dirpath / item.filename))
                logger.debug(f"Followed link {item.filename}: {target}")

                # Replace out item object with the `stat` of the actual destination
                stat_to_eval = self.sftp_client.stat(target)

            if what == "files":
                if stat.S_ISREG(stat_to_eval.st_mode):
                    items.append(item.filename)
            elif what == "dirs":
                if stat.S_ISDIR(stat_to_eval.st_mode):
                    items.append(item.filename)
            else:
                items.append(item.filename)

        return [dirpath / item for item in items]

    #
    # Management stuff
    #

    def close(self):
        self.sftp_client.close()

    def __repr__(self):
        return f"<RemoteLinuxFilesExecutor>"

    def __del__(self):
        logger.debug(f"Closing sftp connection")
        self.close()


class _ExecutorManager:
    _executors = {}
    _lock = threading.Lock()  # Lock to prevent threading issues

    @classmethod
    def get_executor(cls, host: str):
        # Local hosts aren't cached, as they don't require state
        # management
        if host in LOCAL_HOSTS:
            return LocalLinuxFilesExecutor()

        with cls._lock:
            return cls._get_remote_executor(host)

    @classmethod
    def _get_remote_executor(cls, host, retries=3):
        if host not in cls._executors:
            logger.debug(f"Creating new SFTP connection to {host}")
            try:
                ssh_executor: RemoteLinuxShellExecutor = get_linux_shell_executor(host)
                cls._executors[host] = RemoteLinuxFilesExecutor(ssh_executor)
            except Exception as e:
                if retries > 0:
                    logger.debug(
                        f"Failed to create new SSH connection to {host}: {e}. Retrying... ({retries} left",
                        exc_info=True,
                    )
                    return cls._get_remote_executor(host, retries - 1)

                logger.error(f"Failed to create new SSH connection to {host}")
                raise e

        connection: RemoteLinuxFilesExecutor = cls._executors[host]

        # Check if the connection is still live
        # Using an actual packet, as is_active() returns false positives
        try:
            transport = connection.shell_executor.ssh_client.get_transport()
            transport.send_ignore()
        except Exception as e:
            del cls._executors[host]
            return cls._get_remote_executor(host, retries)

        return cls._executors[host]

    @classmethod
    def close_connection(cls, host):
        if host in LOCAL_HOSTS:
            return

        with cls._lock:
            if host in cls._executors:
                del cls._executors[host]

    @classmethod
    def close_all(cls):
        with cls._lock:
            for ssh in cls._executors.values():
                ssh.close()
            cls._executors.clear()


def get_executor(host: str) -> LinuxFilesExecutor:
    logger.debug(f"Getting files executor for host: {host}")
    return _ExecutorManager.get_executor(host)


def close_connection(host: str):
    logger.debug(f"Closing files executor for host: {host}")
    _ExecutorManager.close_connection(host)
