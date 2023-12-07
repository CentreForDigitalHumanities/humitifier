from typing import Literal

SEVERITY = Literal["info", "warning", "critical"]


def missing_metadata(host) -> tuple[SEVERITY, str] | None:
    if host.metadata == {} or host.metadata is None:
        return "warning", "No metadata defined for host"


def missing_contact(host) -> tuple[SEVERITY, str] | None:
    if missing_metadata(host):
        return None
    if host.metadata.get("contact") is None:
        return "info", "No contact defined for host"


def scan_exception(host) -> tuple[SEVERITY, str] | None:
    if host.facts is None or host.facts.exceptions:
        return "critical", "Scan failed for host"


ALERTS = [missing_metadata, missing_contact, scan_exception]