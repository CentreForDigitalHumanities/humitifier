from dataclasses import asdict, dataclass


@dataclass
class HostnameCtl:
    hostname: str
    os: str
    cpe_os_name: str | None
    kernel: str
    virtualization: str | None

    @classmethod
    @property
    def alias(cls) -> str:
        return "hostnamectl"

    @staticmethod
    def _parse_line(line: str) -> tuple[str, str]:
        label, _, value = line.strip().partition(":")
        match label:
            case "Static hostname":
                create_arg = "hostname"
            case "Operating System":
                create_arg = "os"
            case "CPE OS Name":
                create_arg = "cpe_os_name"
            case "Kernel":
                create_arg = "kernel"
            case "Virtualization":
                create_arg = "virtualization"
            case _:
                return None, None
        return create_arg, value.strip()

    @classmethod
    def from_stdout(cls, output: list[str]) -> "HostnameCtl":
        base_args = {
            "virtualization": None,
            "cpe_os_name": None,
        }
        parsed_props = [cls._parse_line(line) for line in output]
        parsed_args = {k: v for k, v in parsed_props if k is not None}
        return cls(**{**base_args, **parsed_args})

    @staticmethod
    def ssh_command(_) -> str:
        return "hostnamectl"

    @classmethod
    def from_sql(cls, sql_data) -> "HostnameCtl":
        return cls(**sql_data)

    def to_sql(self):
        return asdict(self)
