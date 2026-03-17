"""Manual scan CLI command implementation."""

from typing import Optional
from pydantic import BaseModel, Field

from humitifier_common.scan_data import ScanInput
from humitifier_scanner.scanner import scan
from humitifier_scanner.utils import get_local_fqdn

from .artefact_parser import collect_requested_artefacts, build_artefact_scan_options


class ManualScan(BaseModel):
    """Run a manual scan on a single host.
    Data is not reported back to the server; this command is meant for retrieving
    data over multiple servers for 'quick local scans'; see also the `cli` artefacts.
    """

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

        # Collect and parse artefacts
        requested_artefacts = collect_requested_artefacts(
            self.artefact, self.artefact_group
        )

        artefacts = build_artefact_scan_options(requested_artefacts)

        # Run the scan
        scan_input = ScanInput(
            hostname=self.host,
            artefacts=artefacts,
        )

        result = scan(scan_input)

        # Handle the results
        print(result.model_dump_json(indent=self.indent_results))
