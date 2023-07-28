from abc import abstractmethod
from typing import Protocol, runtime_checkable

@runtime_checkable
class SshFact(Protocol):

    @classmethod
    @property
    @abstractmethod
    def alias(cls) -> str: ...

    @classmethod
    @abstractmethod
    def from_stdout(cls, stdout: list[str]): ...

    @staticmethod
    @abstractmethod
    def ssh_command(host) -> str: ...
