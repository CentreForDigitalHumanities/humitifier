import os
import toml
from dataclasses import dataclass

from pssh.clients.native import ParallelSSHClient

CONF_FILE = os.environ.get("HUMITIFIER_CONFIG", ".local/app_config.toml")


@dataclass
class Config:
    db: str
    migrations_dir: str
    inventory: list[str]
    pssh: dict
    tasks: dict[str, str]


with open(CONF_FILE) as cfg_file:
    data = toml.load(cfg_file)

CONFIG = Config(**data)
PSSH_CLIENT = ParallelSSHClient(CONFIG.inventory, **CONFIG.pssh)
