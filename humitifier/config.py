import os
import toml
from dataclasses import dataclass

from pssh.clients.native import ParallelSSHClient

from humitifier.logging import logging

CONF_FILE = os.environ.get("HUMITIFIER_CONFIG", ".local/app_config.toml")


@dataclass
class Config:
    db: str
    migrations_dir: str
    inventory: list[str]
    pssh: dict
    tasks: dict[str, str]

    @classmethod
    def load(cls) -> "Config":
        with open(CONF_FILE) as cfg_file:
            data = toml.load(cfg_file)

        inventory_set = set(data["inventory"])
        if len(inventory_set) != len(data["inventory"]):
            logging.warning("Duplicate entries in inventory")
        data["inventory"] = list(inventory_set)
        return cls(**data)


CONFIG = Config.load()
PSSH_CLIENT = ParallelSSHClient(CONFIG.inventory, **CONFIG.pssh)
