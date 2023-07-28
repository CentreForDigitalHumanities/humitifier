from dataclasses import dataclass


@dataclass
class Group:
    name: str
    gid: int
    users: list[str]

    @classmethod
    def from_line(cls, output_line: list[str]) -> list["Group"]:
        name, _, gid, users = output_line.strip().split(":")
        users = [] if users == "" else users.split(",")
        return cls(name=name, gid=int(gid), users=users)


class Groups(list[Group]):

    @classmethod
    @property
    def alias(cls) -> str:
        return "groups"

    @classmethod
    def from_stdout(cls, output: list[str]) -> "Groups":
        return cls([Group.from_line(line) for line in output])
    
    @staticmethod
    def ssh_command(_) -> str:
        return "cat /etc/group"