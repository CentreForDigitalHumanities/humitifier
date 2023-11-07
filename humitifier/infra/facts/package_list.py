from dataclasses import asdict, dataclass


@dataclass
class Package:
    name: str
    version: str

    @classmethod
    def from_line(cls, output_line: str) -> "Package":
        name, _, version = output_line.strip().partition("\t")
        return cls(name=name, version=version)

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def tooltip(self) -> str:
        return f"version: {self.version}"


class PackageList(list[Package]):
    @classmethod
    @property
    def alias(cls) -> str:
        return "package-list"

    @classmethod
    def from_stdout(cls, output: list[str]) -> "PackageList":
        return cls([Package.from_line(line) for line in output])

    @staticmethod
    def ssh_command(_) -> str:
        return (
            "command -v dpkg-query >/dev/null 2>&1 && "
            "dpkg-query -W -f='${Package}\t${Version}\n' || "
            "rpm -qa --queryformat '%{NAME}\t%{VERSION}\n'"
        )

    @classmethod
    def from_sql(cls, sql_data) -> "PackageList":
        return cls([Package(**pkg) for pkg in sql_data])

    def to_sql(self):
        return [asdict(pkg) for pkg in self]
