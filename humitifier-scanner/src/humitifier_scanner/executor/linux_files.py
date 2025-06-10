import abc
import stat
import threading
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal, TextIO

from paramiko import SFTPClient, SFTPFile
import paramiko
import socket

from humitifier_scanner.logger import logger

from .shared import LOCAL_HOSTS

from .linux_shell import (
    RemoteLinuxShellExecutor,
    get_executor as get_linux_shell_executor,
)


class LinuxFilesExecutor(abc.ABC):
    """
    Abstract base class that provides a uniform interface for working with files and directories
    in both local and SSH contexts.

    Currently we support local and SSH contexts.

    :ivar _check_path: Validates and potentially converts a given path to an absolute ``Path``
        object. Ensures only absolute paths are used throughout operations.
    :type _check_path: static method
    """

    def open(self, filename: str | Path) -> TextIO | SFTPFile:
        """
        Open a file given its path, ensuring consistent read-only behavior across both
        local and SSH contexts.

        Do note that paths must always be absolute; we do NOT have a cwd context we
        manage.

        :param filename: The path to the file to open, provided either as a string or a Path object.
        :type filename: str | Path
        :return: A file-like object representing the opened file.
        :rtype: TextIO | SFTPFile
        :raises FileNotFoundError: If the specified file cannot be found.
        """
        logger.debug(f"Opening file {filename}")

        filename = self._check_path(filename)

        try:
            # SSH is always rb, so we force it rb on local for consistency
            return self._open(filename, "rb")
        except FileNotFoundError as e:
            logger.error(f"File {filename} not found: {e}")
            raise e

    def list_dir(
        self, dirpath: str | Path, what: Literal["files", "dirs", "both"] = "files"
    ) -> list[Path]:
        """
        Lists contents of a directory based on the specified type.

        Do note that paths must always be absolute; we do NOT have a cwd context we
        manage.

        :param dirpath: Directory path to list contents from, either as a string
            or Path object.
        :param what: Specifies what to list from the directory. Possible values
            are "files", "dirs", or "both". Defaults to "files".
        :return: A list of Path objects representing the contents of the directory.
        :rtype: list[Path]
        """
        dirpath = self._check_path(dirpath)

        logger.debug(f"Listing directory {dirpath}")

        return self._list_dir(dirpath, what)

    def create_shadow_copy(self, source_dir: Path | str):
        """Untested, do not use unless you want pain"""
        source_dir = self._check_path(source_dir)
        return RootShadowCopy(self, source_dir)

    def _copy(self, source: Path | str, target: Path | str):
        source = self._check_path(source)
        target = self._check_path(target, False)

        return self._cp(source, target)

    @staticmethod
    def _check_path(p: str | Path, needs_absolute: bool = True) -> Path:
        if not isinstance(p, Path):
            p = Path(p)

        if needs_absolute and not p.is_absolute():
            logger.error(f"Path {p} is not a absolute path")
            logger.error(type(p))
            raise ValueError("Path must be a absolute path")

        return p

    ##
    ## Implementation specific
    ##

    @abc.abstractmethod
    def _open(self, filename: Path, mode: str) -> TextIO | SFTPFile:
        pass

    @abc.abstractmethod
    def _cp(self, source: Path, target: Path):
        pass

    @abc.abstractmethod
    def _list_dir(
        self, dirpath: Path, what: Literal["files", "dirs", "both"]
    ) -> list[Path]:
        pass


class LocalLinuxFilesExecutor(LinuxFilesExecutor):
    """
    Represents a local file executor inheriting from LinuxFilesExecutor.

    This class provides functionalities to open files, copy files, and list
    contents of directories using the local filesystem. Designed for tasks
    that involve manipulating files and directories on Linux-based systems.
    Each method encapsulates specific file-related operations, applying
    appropriate validations and exceptions as necessary.
    """

    def _open(self, filename: Path, mode: str) -> TextIO:
        if mode not in ["r", "rb", "rt"]:
            raise ValueError("Mode must be 'r' or 'rb'")

        return open(filename, mode)

    def _cp(self, source: Path, target: Path):
        if not source.exists():
            raise FileNotFoundError(f"Source file does not exist: {source}")
        if source.is_dir():
            raise IsADirectoryError(f"Source is a directory, not a file: {source}")

        logger.debug(f"Copying file from {source} to {target}")
        shutil.copy(source, target)

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
    """
    Handles file operations on a remote Linux system using SFTP.

    This class extends LinuxFilesExecutor to work with files and directories on a
    remote Linux machine. It uses a RemoteLinuxShellExecutor instance to manage
    connection and execution of commands through SSH and SFTP protocols. The
    primary purpose of this class is to facilitate file operations such as opening
    files, file copying, and directory listing over a secure channel.

    :ivar shell_executor: Executor for managing remote shell commands.
    :type shell_executor: RemoteLinuxShellExecutor
    :ivar sftp_client: SFTP client for managing file operations.
    :type sftp_client: paramiko.sftp_client.SFTPClient
    """

    def __init__(self, shell_executor: RemoteLinuxShellExecutor):
        super().__init__()
        self.shell_executor = shell_executor
        self.sftp_client: SFTPClient = None
        self._connect()

    def _connect(self):
        self.sftp_client: SFTPClient = self.shell_executor.ssh_client.open_sftp()

    def _reconnect(self):
        self.close()
        self.shell_executor._reconnect()
        self._connect()

    def _with_reconnect_retry(self, func, *args, **kwargs):
        retry = False
        while True:
            try:
                return func(*args, **kwargs)
            except (paramiko.ssh_exception.SSHException, OSError, socket.error) as e:
                if not retry:
                    logger.warning(f"SSH error in {func.__name__}(), retrying after reconnect: {e}")
                    self._reconnect()
                    retry = True
                    continue
                raise

    def _open(self, filename: Path, mode: str) -> SFTPFile:
        if mode not in ["r", "rb", "rt"]:
            raise ValueError("Mode must be 'r' or 'rb'")
        return self._with_reconnect_retry(self.sftp_client.open, str(filename), mode)

    def _cp(self, source: Path, target: Path):
        logger.debug(f"Copying file from {source} to {target}")
        return self._with_reconnect_retry(self.sftp_client.get, str(source), str(target))

    def _list_dir(
        self, dirpath: Path, what: Literal["files", "dirs", "both"]
    ) -> list[Path]:
        def do_list():
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
        try:
            return self._with_reconnect_retry(do_list)
        except FileNotFoundError:
            return []

    #
    # Management stuff
    #

    def close(self):
        if self.sftp_client:
            self.sftp_client.close()

    def __repr__(self):
        return f"<RemoteLinuxFilesExecutor>"

    def __del__(self):
        logger.debug(f"Closing sftp connection")
        self.close()


class RootShadowCopy:
    def __init__(self, executor: LinuxFilesExecutor, source_dir: Path):
        self.executor = executor
        self.tmpdir = TemporaryDirectory(delete=False)

        self._copy_dir(source_dir, Path(self.tmpdir.name))

    def _copy_dir(self, source_dir: Path, target_dir: Path):
        logger.debug(f"Copying directory {source_dir} to {target_dir}")
        for subdir in self.executor.list_dir(source_dir, what="dirs"):
            source_path = source_dir / subdir.name
            target_path = target_dir / subdir.name
            target_path.mkdir(parents=True, exist_ok=True)
            self._copy_dir(source_path, target_path)

        for file in self.executor.list_dir(source_dir, what="files"):
            self.executor._copy(file, target_dir / file.name)

    def __enter__(self):
        return self.tmpdir.name

    def __exit__(self, exc, value, traceback):
        self.tmpdir.cleanup()


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
