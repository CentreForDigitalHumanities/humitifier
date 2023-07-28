from dataclasses import dataclass


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
