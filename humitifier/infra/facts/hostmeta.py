import json
from dataclasses import asdict, dataclass


@dataclass
class HostMeta:
    department: str | None
    contact: str | None
    update_policy: dict[str, bool] | None
    webdav: str | None
    vhosts: list[dict] | None
    fileservers: list[str] | None
    databases: dict[dict[str, list[str]]] | None

    @classmethod
    @property
    def alias(cls) -> str:
        return "hostmeta"

    @classmethod
    def from_stdout(cls, output: list[str]) -> "HostMeta":
        base_args = {
            "department": None,
            "contact": None,
            "update_policy": None,
            "webdav": None,
            "vhosts": None,
            "fileservers": None,
            "databases": None,
        }
        if output[0] == "cat: /hum/doc/server_facts.json: No such file or directory":
            return cls(**base_args)
        json_str = "\n".join(output)
        json_args = json.loads(json_str)
        return cls(**{**base_args, **json_args})

    @staticmethod
    def ssh_command(_) -> str:
        return "cat /hum/doc/server_facts.json"

    @classmethod
    def from_sql(cls, sql_data) -> "HostMeta":
        return cls(**sql_data)

    def to_sql(self):
        return asdict(self)
