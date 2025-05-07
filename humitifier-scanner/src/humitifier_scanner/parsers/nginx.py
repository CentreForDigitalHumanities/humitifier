import tempfile
from pprint import pformat

from reconfigure.parsers import NginxParser

from humitifier_common.artefacts import (
    Webhost,
    WebhostAuth,
    WebhostLocation,
    WebhostProxy,
    WebhostRewriteRule,
)
from humitifier_scanner.executor.linux_files import LinuxFilesExecutor
from humitifier_scanner.logger import logger


class NginxConfigParser:
    # Parser modes
    # Determines which set of line-handlers will be used
    DEFAULT_LOOP = "default_loop"
    LOCATION_LOOP = "location_loop"

    @classmethod
    def parse(cls, filename, files_executor: LinuxFilesExecutor) -> list[Webhost]:
        return cls(filename, files_executor)._parse()

    def __init__(self, filename, files_executor: LinuxFilesExecutor):
        self.filename = filename

        self.files_executor = files_executor

        with self.files_executor.open(filename) as f:
            self.contents = f.read()

    def _parse(self) -> list[Webhost]:
        webhosts: list[Webhost] = []
        config_files = self.files_executor.list_dir("/etc/nginx/sites-enabled/")

        for config_file in config_files:

            data = self.files_executor.open(config_file).read()
            data = str(data, "utf-8")

            result = NginxParser().parse(data)

            for server in result:
                listen_ports: list[int] = []
                document_root: str = ""
                hostname: str = ""
                hostname_aliases: list[str] = []
                locations: dict[str, WebhostLocation] = {}
                includes: list[str] = []

                for item in server:
                    if item.name == "listen":
                        port = item.value
                        if ":" in port:
                            port = port.split(":", maxsplit=1)[1]

                        if " " in port:
                            port = port.split(" ", maxsplit=1)[0]

                        try:
                            port = int(port)
                            listen_ports.append(port)
                        except:
                            pass

                    elif item.name == "server_name":
                        server_names = item.value.split(" ")
                        if not hostname:
                            hostname = server_names[0]
                            del server_names[0]

                        hostname_aliases += server_names

                    elif item.name == "root":
                        document_root = item.value

                    elif item.name == "include":
                        includes.append(item.value)

                    elif item.name == "location":
                        location_path = item.parameter
                        location_root = None
                        proxy: WebhostProxy | None = None
                        auth: WebhostAuth | None = None
                        rewrite_rules: list[WebhostRewriteRule] = []

                        for location_item in item.children:
                            if location_item.name == "root":
                                location_root = location_item.value
                            elif location_item.name == "include":
                                includes.append(location_item.value)

                            elif location_item.name == "return":
                                rewrite_rules.append(
                                    {
                                        "conditions": [],
                                        "rule": location_item.value,
                                    }
                                )

                            elif location_item.name == "auth_basic":
                                auth = {
                                    "type": "basic",
                                    "provider": None,
                                }

                            elif location_item.name.endswith("_pass"):
                                proxy_type = location_item.name.rsplit("_", maxsplit=1)[
                                    0
                                ]
                                proxy = {
                                    "type": proxy_type,
                                    "endpoint": location_item.value,
                                }

                        locations[location_path] = {
                            "document_root": location_root,
                            "proxy": proxy,
                            "auth": auth,
                            "rewrite_rules": rewrite_rules,
                        }

                webhosts.append(
                    {
                        "listen_ports": listen_ports,
                        "webserver": "nginx",
                        "filename": str(config_file),
                        "document_root": document_root,
                        "hostname": hostname,
                        "hostname_aliases": hostname_aliases,
                        "locations": locations,
                        "rewrite_rules": [],
                        "includes": includes,
                    }
                )

        return webhosts
