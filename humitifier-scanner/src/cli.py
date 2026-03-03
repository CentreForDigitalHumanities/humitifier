#!/usr/bin/env python3
import json
import time

import sys
from enum import Enum
from pprint import pprint
from typing import Optional
import logging
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

import toml
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    CliApp,
    CliImplicitFlag,
    CliSubCommand,
    SettingsConfigDict,
)
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text

from humitifier_scanner.api import HumitifierAPIClient
from humitifier_scanner.config import (
    Settings,
    _CONFIG_LOCATIONS,
    _SECRETS_DIR,
)
from humitifier_scanner.scanner import scan
from humitifier_common.scan_data import ArtefactScanOptions, ScanInput
from humitifier_common.artefacts import registry as artefact_registry
from humitifier_scanner.logger import logger
from humitifier_scanner.utils import get_local_fqdn


##
## CLI commands
##
class BulkManualScan(BaseModel):
    hosts_file: str = Field(
        description="File containing a list of hosts to scan, one per line"
    )

    progress: CliImplicitFlag[bool] = Field(
        default=False,
        description="Show progress bar and scan output during scans",
    )

    artefact: list[str] = Field(
        default_factory=list,
        description="Fact to scan; multiple can be specified by repeating the "
        "option. If used in combination with the 'fact_group' "
        "option, add an '!' prefix to explicitly disable one fact in a group.",
    )
    artefact_group: list[str] = Field(
        default_factory=list,
        description="Fact group to scan; multiple can be specified by "
        "repeating the option. Individual facts can still be overridden with "
        "the 'fact' option. ",
    )

    indent_results: Optional[int] = Field(
        4,
        description="Indentation level for the printed results",
    )

    output_file: Optional[str] = Field(
        default=None, description="Output file for combined results"
    )

    debug_output_file: Optional[str] = Field(
        default=None, description="Optional file to pipe scan output for debugging"
    )

    def cli_cmd(self):

        if not self.hosts_file:
            raise ValueError("hosts_file is None")

        with open(self.hosts_file, "r") as f:
            hosts = f.read().splitlines()

        # Collect all requested artefacts

        requested_artefacts = []
        # Add all facts from the requested groups
        for group in self.artefact_group:
            requested_artefacts.extend(
                [
                    fact.__artefact_name__
                    for fact in artefact_registry.get_all_in_group(group)
                ]
            )

        # Add any individual facts
        for artefact in self.artefact:
            artefact_name = artefact
            knockout = artefact_name.startswith("!")
            variant = "default"

            # Remove the knockout prefix
            if knockout:
                artefact_name = artefact_name[1:]

            if ":" in artefact:
                artefact_name, variant = artefact.split(":", 1)

            # Check if the artefact is already in the requested facts list
            # If so, remove it and add the explicitly specified artefact
            # (This makes sure we can manually override the used variant)
            if artefact_name in requested_artefacts:
                requested_artefacts.remove(artefact_name)

            if not knockout:
                requested_artefacts.append(f"{artefact_name}:{variant}")

        # Transform the requested facts into the instructions for the scanner

        artefacts: dict[str, ArtefactScanOptions] = {}

        for artefact in requested_artefacts:
            options = {}
            if ":" in artefact:
                artefact, variant = artefact.split(":", 1)
                options["variant"] = variant
            artefacts[artefact] = ArtefactScanOptions(**options)

        combined = []

        if self.progress:
            # Use rich progress display
            console = Console()
            debug_log = []

            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeRemainingColumn(),
                console=console,
            ) as progress:

                task_id = progress.add_task("[cyan]Scanning hosts...", total=len(hosts))

                for idx, host in enumerate(hosts):
                    current_time = time.time()

                    # Create layout for the current scan
                    layout = Layout()
                    layout.split_column(
                        Layout(name="progress", size=3),
                        Layout(name="current", size=3),
                        Layout(name="output")
                    )

                    # Capture stdout/stderr during scan
                    output_capture = StringIO()

                    with redirect_stdout(output_capture), redirect_stderr(output_capture):
                        # Run the scan
                        scan_input = ScanInput(
                            hostname=host,
                            artefacts=artefacts,
                        )

                        result = scan(scan_input)

                    # Get captured output
                    captured_output = output_capture.getvalue()
                    if captured_output:
                        debug_log.append(f"\n=== {host} ===\n{captured_output}")

                    # Handle the results
                    combined.append(result.model_dump())
                    elapsed = time.time() - current_time

                    # Update progress
                    progress.update(
                        task_id,
                        advance=1,
                        description=f"[cyan]Scanning hosts... [green]{host}[/green] completed in {elapsed:.2f}s"
                    )

                    # Show output in console
                    if captured_output:
                        console.print(Panel(
                            Text(captured_output, overflow="fold"),
                            title=f"Output from {host}",
                            border_style="green"
                        ))

            # Write debug output if requested
            if self.debug_output_file and debug_log:
                with open(self.debug_output_file, "w") as f:
                    f.write("".join(debug_log))
                console.print(f"\n[green]Debug output written to {self.debug_output_file}[/green]")
        else:
            # Simple non-progress mode
            for host in hosts:
                # Run the scan
                scan_input = ScanInput(
                    hostname=host,
                    artefacts=artefacts,
                )

                result = scan(scan_input)

                # Handle the results
                combined.append(result.model_dump())

        if self.output_file:
            with open(self.output_file, "w") as f:
                json.dump(combined, f, indent=self.indent_results, default=str)
        else:
            json.dump(combined, sys.stdout, indent=self.indent_results, default=str)


class ManualScan(BaseModel):
    host: str | None = Field(
        None,
        description="Hostname to scan; defaults to the local host",
    )

    artefact: list[str] = Field(
        default_factory=list,
        description="Fact to scan; multiple can be specified by repeating the "
        "option. If used in combination with the 'fact_group' "
        "option, add an '!' prefix to explicitly disable one fact in a group.",
    )
    artefact_group: list[str] = Field(
        default_factory=list,
        description="Fact group to scan; multiple can be specified by "
        "repeating the option. Individual facts can still be overridden with "
        "the 'fact' option. ",
    )

    indent_results: Optional[int] = Field(
        4,
        description="Indentation level for the printed results",
    )

    def cli_cmd(self):

        if not self.host:
            self.host = get_local_fqdn()

        # Collect all requested artefacts

        requested_artefacts = []
        # Add all facts from the requested groups
        for group in self.artefact_group:
            requested_artefacts.extend(
                [
                    fact.__artefact_name__
                    for fact in artefact_registry.get_all_in_group(group)
                ]
            )

        # Add any individual facts
        for artefact in self.artefact:
            artefact_name = artefact
            knockout = artefact_name.startswith("!")
            variant = "default"

            # Remove the knockout prefix
            if knockout:
                artefact_name = artefact_name[1:]

            if ":" in artefact:
                artefact_name, variant = artefact.split(":", 1)

            # Check if the artefact is already in the requested facts list
            # If so, remove it and add the explicitly specified artefact
            # (This makes sure we can manually override the used variant)
            if artefact_name in requested_artefacts:
                requested_artefacts.remove(artefact_name)

            if not knockout:
                requested_artefacts.append(f"{artefact_name}:{variant}")

        # Transform the requested facts into the instructions for the scanner

        artefacts: dict[str, ArtefactScanOptions] = {}

        for artefact in requested_artefacts:
            options = {}
            if ":" in artefact:
                artefact, variant = artefact.split(":", 1)
                options["variant"] = variant
            artefacts[artefact] = ArtefactScanOptions(**options)

        # Run the scan
        scan_input = ScanInput(
            hostname=self.host,
            artefacts=artefacts,
        )

        result = scan(scan_input)

        # Handle the results
        print(result.model_dump_json(indent=self.indent_results))


class Scan(BaseModel):
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

    def cli_cmd(self):
        print(get_local_fqdn())


class RetrieveScanSpec(BaseModel):
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
