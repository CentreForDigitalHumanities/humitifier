import os
import toml
from dataclasses import dataclass

CONF_FILE = os.environ.get("HUMITIFIER_CONFIG", ".local/app_config.toml")


@dataclass
class Config:
    db: str
    inventory: str
    pssh: dict
    tasks: dict[str, str]


with open(CONF_FILE) as cfg_file:
    data = toml.load(cfg_file)
    CONFIG = Config(**data)
