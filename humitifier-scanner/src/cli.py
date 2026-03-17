#!/usr/bin/env python3
import sys
from enum import Enum
from pprint import pprint
from typing import Optional
import logging

import toml
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    CliApp,
    CliImplicitFlag,
    CliSubCommand,
    SettingsConfigDict,
)

from humitifier_common.artefacts import registry as artefact_registry
from humitifier_scanner.api import HumitifierAPIClient
from humitifier_scanner.config import (
    Settings,
    _CONFIG_LOCATIONS,
    _SECRETS_DIR,
)
from humitifier_scanner.collectors.backend import registry as collector_registry
from humitifier_scanner.scanner import scan
from humitifier_scanner.logger import logger
from humitifier_scanner.utils import get_local_fqdn
from humitifier_scanner.cli_commands import ManualScan, BulkManualScan


##
## CLI commands
##
class Scan(BaseModel):
    """Main scan command; retrieves scan spec from API and runs scan according to
    that specification. Will also upload results back to the API.
    Use manual_scan or bulk_scan if you want to retrieve info locally/without
    the server API."""

    host: str | None = Field(
        None,
        description="Hostname to scan; defaults to the local host",
    )

    def cli_cmd(self):
        if not self.host:
            self.host = get_local_fqdn()

        api_client = HumitifierAPIClient()

        scan_spec = api_client.get_scan_spec(self.host)

        if not scan_spec:
            print("Did not receive scan_spec from API")
            sys.exit(1)

        result = scan(scan_spec)

        ok = api_client.upload_scan(result)

        if ok:
            print("Scan successful")
        else:
            print("Scan failed - could not upload results")


class OutputFormatEnum(Enum):
    toml = "toml"
    pydantic = "pydantic"
    raw = "raw"


class PrintConfig(BaseModel):
    output_format: OutputFormatEnum = Field(
        OutputFormatEnum.toml, description="Output format"
    )

    def cli_cmd(self):
        from humitifier_scanner.config import CONFIG

        if self.output_format == OutputFormatEnum.toml:
            print(toml.dumps(CONFIG.model_dump()))
        elif self.output_format == OutputFormatEnum.pydantic:
            pprint(CONFIG)
        elif self.output_format == OutputFormatEnum.raw:
            pprint(CONFIG.model_dump())


class Hostname(BaseModel):
    """Print the hostname Humitifier Scanner thinks is the name of the local host."""

    def cli_cmd(self):
        print(get_local_fqdn())


class RetrieveScanSpec(BaseModel):
    """Retrieve and print the scan spec that the scan command will use from the
    server."""

    host: str | None = Field(
        None,
        description="Hostname to scan; defaults to the local host",
    )

    def cli_cmd(self):
        if not self.host:
            self.host = get_local_fqdn()

        print(self.host)

        api_client = HumitifierAPIClient()

        scan_spec = api_client.get_scan_spec(self.host)

        if not scan_spec:
            print("Did not receive scan_spec")
            sys.exit(1)

        print(scan_spec.model_dump_json(indent=4))


class PrintArtefacts(BaseModel):
    """Print the artefacts that are supported by Humitifier Scanner. If multiple
    collectors are available for an artefact, they will be listed in parentheses."""

    group: Optional[str] = Field(
        None,
        description="Artefact group to print; if not specified, all artefacts will be printed",
    )

    def cli_cmd(self):
        if self.group:
            artefacts = artefact_registry.get_all_in_group(self.group)
        else:
            artefacts = artefact_registry.all_available

        print("Available artefacts:")
        for artefact in artefacts:
            variants = list(collector_registry.get_variants_for_artefact(artefact))
            print(
                f"  - {artefact} ({', '.join(variants)})"
                if variants
                else f"  - {artefact}"
            )


class PrintArtefactGroups(BaseModel):
    """Print the artefact groups that are supported by Humitifier Scanner."""

    def cli_cmd(self):
        print("Available artefact groups:")
        for group in artefact_registry.available_groups:
            print(f"  - {group}")


##
## Main config for CLI
##
class CLISettings(Settings, BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="humitifier_scanner_",
        env_nested_delimiter="__",
        cli_parse_args=True,
        cli_prog_name="humitifier-scanner",
        toml_file=_CONFIG_LOCATIONS,
        secrets_dir=_SECRETS_DIR,
    )

    ##
    ## CLI options
    ##

    debug: CliImplicitFlag[bool] = Field(
        False,
        description="Enable debug mode",
    )

    ##
    ## CLI commands
    ##
    scan: CliSubCommand[Scan]
    manual_scan: CliSubCommand[ManualScan]
    bulk_scan: CliSubCommand[BulkManualScan]
    print_config: CliSubCommand[PrintConfig]
    hostname: CliSubCommand[Hostname]
    scan_spec: CliSubCommand[RetrieveScanSpec]
    print_artefacts: CliSubCommand[PrintArtefacts]
    print_artefact_groups: CliSubCommand[PrintArtefactGroups]

    def cli_cmd(self) -> None:
        if self.debug:
            # Enable debug logging
            logger.setLevel("DEBUG")
            # Print log to console
            handler = logging.StreamHandler()
            handler.formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            logger.addHandler(handler)

            oauth_logger = logging.getLogger("requests_oauthlib")
            oauth_logger.setLevel(logging.DEBUG)
            oauth_logger.addHandler(handler)

        CliApp.run_subcommand(self)


if __name__ == "__main__":
    CliApp.run(CLISettings)
