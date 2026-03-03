"""Bulk manual scan CLI command implementation."""

import json
import sys
import time
from typing import Optional
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

from pydantic import BaseModel, Field
from pydantic_settings import CliImplicitFlag
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text

from humitifier_common.scan_data import ScanInput, ScanOutput
from humitifier_scanner.scanner import scan

from .artefact_parser import collect_requested_artefacts, build_artefact_scan_options


def run_single_scan(host: str, artefacts: dict) -> ScanOutput:
    """
    Run a single scan on a host.

    Args:
        host: Hostname to scan
        artefacts: Dictionary of artefact scan options

    Returns:
        ScanOutput from the scan
    """
    scan_input = ScanInput(
        hostname=host,
        artefacts=artefacts,
    )
    return scan(scan_input)


def run_scan_with_output_capture(host: str, artefacts: dict) -> tuple[ScanOutput, str]:
    """
    Run a single scan with captured stdout/stderr.

    Args:
        host: Hostname to scan
        artefacts: Dictionary of artefact scan options

    Returns:
        Tuple of (ScanOutput, captured_output)
    """
    output_capture = StringIO()

    with redirect_stdout(output_capture), redirect_stderr(output_capture):
        result = run_single_scan(host, artefacts)

    captured_output = output_capture.getvalue()
    return result, captured_output


def run_scans_with_progress(
    hosts: list[str], artefacts: dict, debug_output_file: Optional[str] = None
) -> list[dict]:
    """
    Run scans on multiple hosts with progress display.

    Args:
        hosts: List of hostnames to scan
        artefacts: Dictionary of artefact scan options
        debug_output_file: Optional file to write debug output

    Returns:
        List of scan result dictionaries
    """
    console = Console()
    debug_log = []
    combined = []

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:

        task_id = progress.add_task("[cyan]Scanning hosts...", total=len(hosts))

        for host in hosts:
            current_time = time.time()

            # Run the scan with output capture
            result, captured_output = run_scan_with_output_capture(host, artefacts)

            # Store captured output for debug log
            if captured_output:
                debug_log.append(f"\n=== {host} ===\n{captured_output}")

            # Store result
            combined.append(result.model_dump())
            elapsed = time.time() - current_time

            # Update progress
            progress.update(
                task_id,
                advance=1,
                description=f"[cyan]Scanning hosts... [green]{host}[/green] completed in {elapsed:.2f}s",
            )

            # Show output in console
            if captured_output:
                console.print(
                    Panel(
                        Text(captured_output, overflow="fold"),
                        title=f"Output from {host}",
                        border_style="green",
                    )
                )

    # Write debug output if requested
    if debug_output_file and debug_log:
        with open(debug_output_file, "w") as f:
            f.write("".join(debug_log))
        console.print(f"\n[green]Debug output written to {debug_output_file}[/green]")

    return combined


def run_scans_simple(hosts: list[str], artefacts: dict) -> list[dict]:
    """
    Run scans on multiple hosts without progress display.

    Args:
        hosts: List of hostnames to scan
        artefacts: Dictionary of artefact scan options

    Returns:
        List of scan result dictionaries
    """
    combined = []

    for host in hosts:
        result = run_single_scan(host, artefacts)
        combined.append(result.model_dump())

    return combined


def write_results(
    results: list[dict], output_file: Optional[str], indent: Optional[int]
) -> None:
    """
    Write scan results to file or stdout.

    Args:
        results: List of scan result dictionaries
        output_file: Optional output file path
        indent: Indentation level for JSON output
    """
    if output_file:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=indent, default=str)
    else:
        json.dump(results, sys.stdout, indent=indent, default=str)


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

        # Read hosts from file
        with open(self.hosts_file, "r") as f:
            hosts = f.read().splitlines()

        # Collect and parse artefacts
        requested_artefacts = collect_requested_artefacts(
            self.artefact, self.artefact_group
        )

        artefacts = build_artefact_scan_options(requested_artefacts)

        # Run scans with or without progress display
        if self.progress:
            combined = run_scans_with_progress(hosts, artefacts, self.debug_output_file)
        else:
            combined = run_scans_simple(hosts, artefacts)

        # Write results
        write_results(combined, self.output_file, self.indent_results)
