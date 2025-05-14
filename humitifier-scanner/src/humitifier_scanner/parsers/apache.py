from humitifier_common.artefacts import (
    WebhostAuth,
    WebhostAuthRequire,
    WebhostLocation,
    Webhost,
    WebhostProxy,
    WebhostRewriteRule,
)
from humitifier_scanner.executor.linux_files import LinuxFilesExecutor
from humitifier_scanner.logger import logger


class ApacheConfigParser:
    # Parser modes
    # Determines which set of line-handlers will be used
    DEFAULT_LOOP = "default_loop"
    LOCATION_LOOP = "location_loop"

    @classmethod
    def parse(cls, filename, files_executor: LinuxFilesExecutor) -> Webhost:
        return cls(filename, files_executor)._parse()

    def __init__(self, filename, files_executor: LinuxFilesExecutor):
        self.filename = filename

        self.files_executor = files_executor

        with self.files_executor.open(filename) as f:
            self.contents = f.readlines()
            self.contents = [str(l, encoding="utf-8") for l in self.contents]
            self.index = 0

        self.listen_ports: list[int] = []
        self.hostname: str = ""
        self.hostname_aliases: list[str] = []
        self.document_root: str = ""
        self.locations: dict[str, WebhostLocation] = {}
        self.rewrite_rules: list[WebhostRewriteRule] = []
        self.includes: list[str] = []

        self.rewrite_conditions = []
        self.current_location = None
        self.mode = self.DEFAULT_LOOP

        self.general_handlers = {
            "ServerName": lambda line: self._set_hostname(line),
            "ServerAlias": lambda line: self._add_hostname_alias(line),
            "DocumentRoot": lambda line: self._set_document_root(line),
            # The space after is needed!
            "ProxyPass ": lambda line: self._add_proxy_pass(line),
            "RewriteCond": lambda line: self._add_rewrite_condition(line),
            "RewriteRule": lambda line: self._add_rewrite_rule(line),
            "<Location": lambda line: self._start_location_block(line),
            "<VirtualHost": lambda line: self._add_virtual_host(line),
            "Include ": lambda line: self._add_include(line),
            "IncludeOptional ": lambda line: self._add_optional_include(line),
        }

        self.location_handlers = {
            "</Location>": lambda line: self._close_location_block(),
            "AuthType": lambda line: self._add_auth_type(line),
            "AuthBasicProvider": lambda line: self._add_auth_provider(line),
            "Require": lambda line: self._add_require(line),
            "Allow": lambda line: self._add_allow(line),
            "Deny": lambda line: self._add_deny(line),
        }

    def _parse(self) -> Webhost:
        while self.index < len(self.contents):
            line = self.contents[self.index].strip()
            self.index += 1

            if self.mode == self.LOCATION_LOOP:
                handlers = self.location_handlers
            else:
                handlers = self.general_handlers

            for key, handler in handlers.items():
                if line.startswith(key):
                    handler(line)
                    break

        return Webhost(
            listen_ports=self.listen_ports,
            webserver="apache",
            filename=str(self.filename),
            hostname=self.hostname,
            hostname_aliases=self.hostname_aliases,
            document_root=self.document_root,
            locations=self.locations,
            rewrite_rules=self.rewrite_rules,
            includes=self.includes,
        )

    ##
    ## Handlers
    ##

    ###
    ### General handlers
    ###

    def _set_hostname(self, line: str) -> None:
        self.hostname = self._extract_value(line, "ServerName")

    def _add_hostname_alias(self, line: str) -> None:
        self.hostname_aliases.append(self._extract_value(line, "ServerAlias"))

    def _set_document_root(self, line: str) -> None:
        raw_root = self._extract_value(line, "DocumentRoot")
        self.document_root = raw_root.strip('"')

    def _add_proxy_pass(self, line: str) -> None:
        sans_prefix = self._extract_value(line, "ProxyPass").strip()
        path, proxy = sans_prefix.split(" ", 1)
        locations = self.locations
        if path not in locations:
            locations[path] = self._initialize_webhost_location()

        if proxy == "!":
            locations[path]["proxy"] = WebhostProxy(
                type="no_proxy",
                endpoint="!",
            )
        else:
            _type, proxy_endpoint = proxy.split(":", 1)
            options = None
            if " " in proxy_endpoint:
                options = {}

                proxy_endpoint, options_segment = proxy_endpoint.split(" ", maxsplit=1)
                raw_options = options_segment.split(" ")

                for raw_option in raw_options:
                    option, value = raw_option.split("=", maxsplit=1)
                    options[option] = value

            locations[path]["proxy"] = WebhostProxy(
                type=_type,
                endpoint=proxy_endpoint,
                options=options,
            )

    def _add_rewrite_condition(self, line: str) -> None:
        self.rewrite_conditions.append(self._extract_value(line, "RewriteCond"))

    def _add_rewrite_rule(self, line: str) -> None:
        rule = self._extract_value(line, "RewriteRule").strip()
        self.rewrite_rules.append({"conditions": self.rewrite_conditions, "rule": rule})
        self.rewrite_conditions = []

    def _start_location_block(self, line: str) -> None:
        location = self._extract_value(line, "<Location", trim_end=True)

        # Strip any surrounding quotes
        if location.startswith('"') and location.endswith('"'):
            location = location[1:-1]

        if location not in self.locations:
            self.locations[location] = self._initialize_webhost_location()
        self.current_location = location
        self.mode = self.LOCATION_LOOP

    def _add_virtual_host(self, line: str) -> None:
        stripped = self._extract_value(line, "<VirtualHost", trim_end=True)
        _, port = stripped.split(":", 1)
        try:
            self.listen_ports.append(int(port))
        except ValueError:
            pass

    def _add_include(self, line: str) -> None:
        include = self._extract_value(line, "Include ").strip()

        if include.startswith('"') and include.endswith('"'):
            include = include[1:-1]

        self._process_include(include)

    def _add_optional_include(self, line: str) -> None:
        include = self._extract_value(line, "IncludeOptional ").strip()

        if include.startswith('"') and include.endswith('"'):
            include = include[1:-1]

        self._process_include(include)

    def _process_include(self, filename):
        if "*" in filename:
            # Just a stupid custom * implementation, nothing to see here
            filename_pre_wildcard = filename[: filename.index("*")]
            filename_post_wildcard = filename[filename.index("*") + 1 :]
            files = self.files_executor.list_dir(filename_pre_wildcard, what="files")
            files = [
                file for file in files if str(file).endswith(filename_post_wildcard)
            ]
        else:
            if (filename.startswith("'") and filename.endswith("'")) or (
                filename.startswith('"') and filename.endswith('"')
            ):
                filename = filename[1:-1]
            files = [filename]

        self.includes.extend(map(str, files))

        try:
            for file in files:
                with self.files_executor.open(file) as include_file:
                    contents = include_file.readlines()
                    contents = [str(l, encoding="utf-8") for l in contents]
                    self.contents[self.index : self.index] = contents

        except FileNotFoundError:
            logger.debug(f"File {filename} not found")

    def _close_location_block(self) -> None:
        self.current_location = None
        self.mode = self.DEFAULT_LOOP

    @staticmethod
    def _parse_virtual_host(line: str, listen_ports: list[int]) -> None:
        stripped = line[len("<VirtualHost") : -1].strip()
        _, port = stripped.split(":", 1)
        try:
            listen_ports.append(int(port))
        except ValueError:
            pass

    ###
    ### Location block handlers
    ###

    def _add_auth_type(self, line: str) -> None:
        current_location_obj = self.locations[self.current_location]

        auth_type = self._extract_value(line, "AuthType")
        if "auth" not in current_location_obj or current_location_obj["auth"] is None:
            current_location_obj["auth"] = self._initialize_webhost_auth()
        current_location_obj["auth"]["type"] = auth_type

    def _add_auth_provider(self, line: str) -> None:
        current_location_obj = self.locations[self.current_location]

        provider = self._extract_value(line, "AuthBasicProvider")
        if "auth" not in current_location_obj or current_location_obj["auth"] is None:
            current_location_obj["auth"] = self._initialize_webhost_auth()
        current_location_obj["auth"]["provider"] = provider

    def _add_require(self, line: str) -> None:
        current_location_obj = self.locations[self.current_location]

        require = self._extract_value(line, "Require")
        if "auth" not in current_location_obj or current_location_obj["auth"] is None:
            current_location_obj["auth"] = self._initialize_webhost_auth()

        negation = False
        items = require.split()

        if items[0] == "not":
            negation = True

        type_index = 1 if negation else 0
        _type = items[type_index]
        values = items[type_index + 1 :]

        current_location_obj["auth"]["requires"].append(
            WebhostAuthRequire(
                type=_type,
                negation=negation,
                values=values,
            )
        )

    def _add_allow(self, line: str) -> None:
        # Rewrite deprecated line to modern syntax
        line = line.replace("Allow", "Require")

        self._add_require(line)

    def _add_deny(self, line: str) -> None:
        # Rewrite deprecated line to modern syntax
        line = line.replace("Deny", "Require not")

        self._add_require(line)

    ##
    ## Helpers
    ##

    @staticmethod
    def _extract_value(line: str, prefix: str, trim_end: bool = False) -> str:
        value = line[len(prefix) :].strip()
        return value[:-1] if trim_end and value.endswith(">") else value

    @staticmethod
    def _initialize_webhost_auth() -> WebhostAuth:
        return {"type": "", "provider": None, "requires": []}

    @staticmethod
    def _initialize_webhost_location() -> WebhostLocation:
        return {
            "document_root": None,
            "auth": None,
            "proxy": None,
            "rewrite_rules": None,
        }

    def _initialize_location_if_needed(self, location: str) -> None:
        if location not in self.locations:
            self.locations[location] = self._initialize_webhost_location()
