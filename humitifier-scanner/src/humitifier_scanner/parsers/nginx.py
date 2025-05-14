from reconfigure.parsers import NginxParser

from humitifier_common.artefacts import (
    Webhost,
    WebhostAuth,
    WebhostLocation,
    WebhostProxy,
    WebhostRewriteRule,
)
from humitifier_scanner.executor.linux_files import LinuxFilesExecutor


class NginxConfigParser:
    # Parser directive constants
    LISTEN = "listen"
    SERVER_NAME = "server_name"
    ROOT = "root"
    INCLUDE = "include"
    LOCATION = "location"
    AUTH_BASIC = "auth_basic"
    RETURN = "return"

    def __init__(self, filename, files_executor: LinuxFilesExecutor):
        self.filename = filename
        self.files_executor = files_executor

    @classmethod
    def parse(cls, filename, files_executor: LinuxFilesExecutor) -> list[Webhost]:
        return cls(filename, files_executor)._parse()

    def _parse(self) -> list[Webhost]:
        config_content = self._read_config_file()
        parsed_data = NginxParser().parse(config_content)
        return [self._process_server_block(server) for server in parsed_data]

    def _read_config_file(self) -> str:
        """Reads and decodes the configuration file content."""
        raw_data = self.files_executor.open(self.filename).read()
        return str(raw_data, "utf-8")

    def _process_server_block(self, server: list) -> Webhost:
        """Processes each server block and extracts relevant information."""
        listen_ports = []
        hostname, hostname_aliases = "", []
        document_root, includes = "", []
        locations = {}

        for directive in server:
            if directive.name == self.LISTEN:
                self._process_listen_directive(directive, listen_ports)
            elif directive.name == self.SERVER_NAME:
                hostname, hostname_aliases = self._process_server_name_directive(
                    directive, hostname, hostname_aliases
                )
            elif directive.name == self.ROOT:
                document_root = directive.value
            elif directive.name == self.INCLUDE:
                includes.append(directive.value)
            elif directive.name == self.LOCATION:
                location_path, location_data, _includes = self._process_location_block(
                    directive
                )
                locations[location_path] = location_data
                includes.extend(_includes)

        return Webhost(
            listen_ports=listen_ports,
            webserver="nginx",
            filename=str(self.filename),
            document_root=document_root,
            hostname=hostname,
            hostname_aliases=hostname_aliases,
            locations=locations,
            rewrite_rules=[],
            includes=includes,
        )

    def _process_listen_directive(self, directive, listen_ports: list[int]) -> None:
        """Extracts and processes the listen ports."""
        port = directive.value
        if ":" in port:
            port = port.split(":", maxsplit=1)[1]
        if " " in port:
            port = port.split(" ", maxsplit=1)[0]
        try:
            listen_ports.append(int(port))
        except ValueError:
            pass

    def _process_server_name_directive(
        self, directive, hostname: str, hostname_aliases: list[str]
    ) -> tuple[str, list[str]]:
        """Extracts hostname and hostname aliases."""
        server_names = directive.value.split(" ")
        if not hostname:
            hostname = server_names.pop(0)
        hostname_aliases += server_names
        return hostname, hostname_aliases

    def _process_location_block(
        self, directive
    ) -> tuple[str, WebhostLocation, list[str]]:
        """Processes a location block and extracts its data."""
        location_path = directive.parameter
        location_root, proxy, auth = None, None, None
        includes = []
        rewrite_rules = []

        for location_directive in directive.children:
            if location_directive.name == self.ROOT:
                location_root = location_directive.value
            elif location_directive.name == self.INCLUDE:
                includes.append(location_directive.value)
            elif location_directive.name == self.RETURN:
                rewrite_rules.append(
                    WebhostRewriteRule(conditions=[], rule=location_directive.value)
                )
            elif location_directive.name == self.AUTH_BASIC:
                auth = WebhostAuth(type="basic", provider=None, requires=[])
            elif location_directive.name.endswith("_pass"):
                proxy = WebhostProxy(
                    type=location_directive.name.rsplit("_", maxsplit=1)[0],
                    endpoint=location_directive.value,
                )

        return (
            location_path,
            WebhostLocation(
                document_root=location_root,
                proxy=proxy,
                auth=auth,
                rewrite_rules=rewrite_rules,
            ),
            includes,
        )
