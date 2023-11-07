from dataclasses import asdict, dataclass


@dataclass
class User:
    name: str
    uid: int
    gid: int
    info: str | None
    home: str
    shell: str

    @classmethod
    def from_line(cls, output_line: str) -> list["User"]:
        name, _, uid, gid, info, home, shell = output_line.strip().split(":")
        info = None if info == "" else info
        return cls(name=name, uid=int(uid), gid=int(gid), info=info, home=home, shell=shell)

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def tooltip(self) -> str:
        return f"uid: {self.uid}, gid: {self.gid}, info: {self.info}, home: {self.home}, shell: {self.shell}"


class Users(list[User]):
    @classmethod
    @property
    def alias(cls) -> str:
        return "users"

    @classmethod
    def from_stdout(cls, output: list[str]) -> "Users":
        return cls([User.from_line(line) for line in output])

    @staticmethod
    def ssh_command(_) -> str:
        return "cat /etc/passwd"

    @classmethod
    def from_sql(cls, sql_data) -> "Users":
        return cls([User(**user) for user in sql_data])

    def to_sql(self):
        return [asdict(user) for user in self]
