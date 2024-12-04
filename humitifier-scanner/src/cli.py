#!/usr/bin/env python3
from enum import Enum
from pprint import pprint
from typing import Optional

import toml
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    CliApp,
    CliPositionalArg,
    CliSubCommand,
    SettingsConfigDict,
)

from humitifier_scanner.config import (
    Settings,
    _CONFIG_LOCATIONS,
    _SECRETS_DIR,
)
from humitifier_scanner.scanner import scan
from humitifier_common.scan_data import FactScanOptions, ScanInput
from humitifier_common.facts import registry as fact_registry


##
## CLI commands
##
class Scan(BaseModel):
    host: str | None = Field(
        None,
        description="Hostname to scan; defaults to the local host",
    )

    fact: list[str] = Field(
        [],
        description="Fact to scan; multiple can be specified by repeating the "
        "option. If used in combination with the 'fact_group' "
        "option, add an '!' prefix to explicitly disable one fact in a group.",
    )
    fact_group: list[str] = Field(
        [],
        description="Fact group to scan; multiple can be specified by "
        "repeating the option. Individual facts can still be overridden with "
        "the 'fact' option. ",
    )

    print_results: bool = Field(
        True,
        description="Print scan results to the console",
    )
    indent_results: Optional[int] = Field(
        None,
        description="Indentation level for the printed results",
    )
    upload_results: bool = Field(
        False,
        description="Upload scan results to the server. Requires API configuration under the 'standalone' options.",
    )
    # TODO: scan profile

    def cli_cmd(self):

        if not self.host:
            self.host = "localhost"

        # Collect all requested facts

        requested_facts = []
        # Add all facts from the requested groups
        for group in self.fact_group:
            requested_facts.extend(
                [
                    fact.__fact_name__
                    for fact in fact_registry.get_all_in_namespace(group)
                ]
            )

        # Add any individual facts
        for fact in self.fact:
            fact_name = fact
            knockout = fact_name.startswith("!")
            variant = "default"

            # Remove the knockout prefix
            if knockout:
                fact_name = fact_name[1:]

            if ":" in fact:
                fact_name, variant = fact.split(":", 1)

            # Check if the fact is already in the requested facts list
            # If so, remove it and add the explicitly specified fact
            # (This makes sure we can manually override the used variant)
            if fact_name in requested_facts:
                requested_facts.remove(fact_name)

            if not knockout:
                requested_facts.append(f"{fact_name}:{variant}")

        # Transform the requested facts into the instructions for the scanner

        facts: dict[str, FactScanOptions] = {}

        for fact in requested_facts:
            options = {}
            if ":" in fact:
                fact, variant = fact.split(":", 1)
                options["variant"] = variant
            facts[fact] = FactScanOptions(**options)

        # Run the scan

        scan_input = ScanInput(
            hostname=self.host,
            facts=facts,
        )

        result = scan(scan_input)

        # Handle the results

        if self.print_results:
            print(result.model_dump_json(indent=self.indent_results))

        if self.upload_results:
            print("Uploading results to the server is not yet implemented.")


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
    ## CLI commands
    ##
    scan: CliSubCommand[Scan]
    print_config: CliSubCommand[PrintConfig]

    def cli_cmd(self) -> None:
        CliApp.run_subcommand(self)


if __name__ == "__main__":
    CliApp.run(CLISettings)
