from enum import Enum

from .linux_shell import (
    close_connection as close_linux_shell_executor,
    get_executor as get_linux_shell_executor,
)
from .linux_files import (
    close_connection as close_linux_file_executor,
    get_executor as get_linux_file_executor,
)


class Executors(Enum):
    SHELL = "shell"
    FILES = "files"


def get_executor(executor: Executors, host: str):
    if executor == Executors.SHELL:
        return get_linux_shell_executor(host)
    elif executor == Executors.FILES:
        return get_linux_file_executor(host)

    raise ValueError(f"Unknown executor: {executor}")


def release_executor(executor: Executors, host: str):
    if executor == Executors.SHELL:
        return close_linux_shell_executor(host)
    elif executor == Executors.FILES:
        return close_linux_file_executor(host)

    raise ValueError(f"Unknown executor: {executor}")
