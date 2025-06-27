from enum import Enum

from .linux_shell import (
    close_connection as close_linux_shell_executor,
    get_executor as get_linux_shell_executor,
)
from .linux_files import (
    close_connection as close_linux_file_executor,
    get_executor as get_linux_file_executor,
)
from .windows_shell import (
    close_connection as close_windows_shell_executor,
    get_executor as get_windows_shell_executor,
)


class Executors(Enum):
    SHELL = "shell"
    FILES = "files"
    WINDOWS_SHELL = "windows_shell"


def get_executor(executor: Executors, host: str):
    if executor == Executors.SHELL:
        return get_linux_shell_executor(host)
    elif executor == Executors.FILES:
        return get_linux_file_executor(host)
    elif executor == Executors.WINDOWS_SHELL:
        return get_windows_shell_executor(host)

    raise ValueError(f"Unknown executor: {executor}")


def release_executor(executor: Executors, host: str):
    if executor == Executors.SHELL:
        return close_linux_shell_executor(host)
    elif executor == Executors.FILES:
        return close_linux_file_executor(host)
    elif executor == Executors.WINDOWS_SHELL:
        return close_windows_shell_executor(host)

    raise ValueError(f"Unknown executor: {executor}")
