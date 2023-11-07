from dataclasses import asdict, dataclass


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

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def tooltip(self) -> str:
        return f"gid: {self.gid}, users: {self.users}"


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

    @classmethod
    def from_sql(cls, sql_data) -> "Groups":
        return cls([Group(**group) for group in sql_data])

    def to_sql(self):
        return [asdict(group) for group in self]
