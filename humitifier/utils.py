from dataclasses import dataclass, asdict


@dataclass
class FactError:
    stdout: str
    stderr: str
    exception: str
    exit_code: int
    py_excpetion: str

    def to_sql(self):
        return asdict(self)


def ssh_command(cmd: str):
    def init_cls(cls):
        cls.cmd = cmd
        return cls

    return init_cls
