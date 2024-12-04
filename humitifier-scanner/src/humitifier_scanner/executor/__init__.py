from enum import Enum

from .linux_shell import close_connection, get_executor as get_linux_shell_executor


class Executors(Enum):
    SHELL = "shell"


def get_executor(executor: Executors, host: str):
    if executor == Executors.SHELL:
        return get_linux_shell_executor(host)

    raise ValueError(f"Unknown executor: {executor}")


def release_executor(executor: Executors, host: str):
    if executor == Executors.SHELL:
        return close_connection(host)

    raise ValueError(f"Unknown executor: {executor}")
