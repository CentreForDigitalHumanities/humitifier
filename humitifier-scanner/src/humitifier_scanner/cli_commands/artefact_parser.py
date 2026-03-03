"""Shared utilities for parsing artefact specifications."""

from humitifier_common.scan_data import ArtefactScanOptions
from humitifier_common.artefacts import registry as artefact_registry


def parse_artefact_name(artefact: str) -> tuple[str, bool, str]:
    """
    Parse an artefact specification string.

    Args:
        artefact: Artefact specification (e.g., "!artefact:variant" or "artefact")

    Returns:
        Tuple of (artefact_name, is_knockout, variant)
    """
    artefact_name = artefact
    knockout = artefact_name.startswith("!")
    variant = "default"

    # Remove the knockout prefix
    if knockout:
        artefact_name = artefact_name[1:]

    if ":" in artefact_name:
        artefact_name, variant = artefact_name.split(":", 1)

    return artefact_name, knockout, variant


def collect_requested_artefacts(
    artefact_list: list[str],
    artefact_group_list: list[str]
) -> list[str]:
    """
    Collect all requested artefacts from groups and individual specifications.

    Args:
        artefact_list: List of individual artefact specifications
        artefact_group_list: List of artefact group names

    Returns:
        List of artefact specifications (with variants)
    """
    requested_artefacts = []

    # Add all facts from the requested groups
    for group in artefact_group_list:
        requested_artefacts.extend(
            [
                fact.__artefact_name__
                for fact in artefact_registry.get_all_in_group(group)
            ]
        )

    # Add any individual facts
    for artefact in artefact_list:
        artefact_name, knockout, variant = parse_artefact_name(artefact)

        # Check if the artefact is already in the requested facts list
        # If so, remove it and add the explicitly specified artefact
        # (This makes sure we can manually override the used variant)
        if artefact_name in requested_artefacts:
            requested_artefacts.remove(artefact_name)

        if not knockout:
            requested_artefacts.append(f"{artefact_name}:{variant}")

    return requested_artefacts


def build_artefact_scan_options(
    requested_artefacts: list[str]
) -> dict[str, ArtefactScanOptions]:
    """
    Transform requested artefacts into scanner instructions.

    Args:
        requested_artefacts: List of artefact specifications (with variants)

    Returns:
        Dictionary mapping artefact names to ArtefactScanOptions
    """
    artefacts: dict[str, ArtefactScanOptions] = {}

    for artefact in requested_artefacts:
        options = {}
        if ":" in artefact:
            artefact, variant = artefact.split(":", 1)
            options["variant"] = variant
        artefacts[artefact] = ArtefactScanOptions(**options)

    return artefacts
