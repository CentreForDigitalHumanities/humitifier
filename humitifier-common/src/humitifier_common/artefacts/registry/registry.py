"""
This module contains code to build and manage the facts registry.
Used by agent/server to retrieve the facts dynamically.
"""

from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from typing import Any

from humitifier_common.utils.pydantic import insert_pydantic_schema_proxy

##
## Registry
##


@dataclass
class ArtefactMetadata:
    # If no data is provided, this is an automatic scan-rejection if true
    essential: bool = False
    # If true, absent data from this artefact will not trigger a warning
    null_is_valid: bool = False


class ArtefactType(Enum):
    FACT = "fact"
    METRIC = "metric"


@dataclass
class ArtefactEntry:
    name: str
    group: str
    artefact: Any
    artefact_type: ArtefactType
    metadata: ArtefactMetadata
    min_version: int = 2
    max_version: int | None = None

    def matches_version(self, version: int) -> bool:
        return version in self._versions

    @cached_property
    def _versions(self) -> set[int]:
        max_v = self.max_version if self.max_version is not None else 1000
        return set(range(self.min_version, max_v + 1))

    def overlaps_with(self, other: "ArtefactEntry") -> bool:
        return bool(self._versions & other._versions)


class _ArtefactRegistry:
    """
    Class to manage the registration and retrieval of facts and metrics (artefacts).

    This class serves as a registry to store, organize, and manage facts and metrics across
    different format versions. Facts and metrics can be categorized by group, and the class provides
    utility functions to retrieve, list, and filter them based on their type, group, and version.
    """

    def __init__(self):
        self._entries: list[ArtefactEntry] = []

    def register(
        self,
        name: str,
        group: str,
        artefact,
        artefact_type: ArtefactType = ArtefactType.FACT,
        metadata: ArtefactMetadata | None = None,
        min_version: int = 2,
        max_version: int | None = None,
    ):
        """
        Registers a fact or metric in the internal registry for a given group, name, and version range.

        :param name: The name of the artefact to register.
        :param group: The group under which the artefact is registered.
        :param artefact: The artefact object / model to associate with the entry.
        :param artefact_type: The type classification (FACT or METRIC).
        :param metadata: ArtefactMetadata instance.
        :param min_version: Lowest format version where this artefact is supported (default 2).
        :param max_version: Highest format version where this artefact is supported (inclusive), or None if unbounded.
        :raises ValueError: If an artefact with the given name and group is already registered with overlapping versions.
        """

        entry = ArtefactEntry(
            name=name,
            group=group,
            artefact=artefact,
            artefact_type=artefact_type,
            metadata=metadata or ArtefactMetadata(),
            min_version=min_version,
            max_version=max_version,
        )

        for existing in self._entries:
            if (
                existing.name == name
                and existing.group == group
                and existing.overlaps_with(entry)
            ):
                raise ValueError(
                    f"Artefact {name} already registered in group {group} for overlapping version range"
                )

        self._entries.append(entry)

        # add meta-variables to the artefact class
        artefact.__artefact_name__ = f"{group}.{name}"
        artefact.__artefact_type__ = artefact_type
        artefact.__artefact_metadata__ = metadata or ArtefactMetadata()
        artefact.__artefact_min_version__ = min_version
        artefact.__artefact_max_version__ = max_version

    @cached_property
    def latest_version(self) -> int:
        """Return the highest version supported across all registered artefacts (defaults to 2)."""
        max_found = 2
        for entry in self._entries:
            if entry.min_version is not None and entry.min_version > max_found:
                max_found = entry.min_version
        return max_found

    @property
    def supported_versions(self) -> list[int]:
        """Return a sorted list of supported format versions from 2 up to latest_version."""
        return list(range(2, self.latest_version + 1))

    def get(
        self,
        name: str,
        group: str | None = None,
        artefact_type: ArtefactType | None = None,
        version: int | None = None,
    ):
        """
        Retrieve an artefact from the registry matching name, optional group, type, and format version.
        Defaults to the latest version if version is not specified.
        """
        if version is None:
            version = self.latest_version

        if group is None:
            if "." in name:
                group, name = name.split(".", 1)
                return self.get(name, group, artefact_type, version=version)

            for entry in self._entries:
                if entry.name == name and entry.matches_version(version):
                    if (
                        artefact_type is not None
                        and entry.artefact_type != artefact_type
                    ):
                        continue
                    return entry.artefact
        else:
            for entry in self._entries:
                if (
                    entry.name == name
                    and entry.group == group
                    and entry.matches_version(version)
                ):
                    if artefact_type is None or entry.artefact_type == artefact_type:
                        return entry.artefact

        return None

    def all(
        self, artefact_type: ArtefactType | None = None, version: int | None = None
    ):
        """
        Retrieve all artefacts for the given format version (defaults to latest),
        optionally filtered by artefact_type.
        """
        if version is None:
            version = self.latest_version

        return [
            entry.artefact
            for entry in self._entries
            if entry.matches_version(version)
            and (artefact_type is None or entry.artefact_type == artefact_type)
        ]

    def all_facts(self, version: int | None = None):
        """Retrieves all facts for the given format version (defaults to latest)."""
        return self.all(ArtefactType.FACT, version=version)

    def all_metrics(self, version: int | None = None):
        """Retrieves all metrics for the given format version (defaults to latest)."""
        return self.all(ArtefactType.METRIC, version=version)

    def get_all_in_group(
        self,
        group: str,
        artefact_type: ArtefactType | None = None,
        version: int | None = None,
    ):
        """Retrieve all artefacts in a group for the given format version (defaults to latest)."""
        if version is None:
            version = self.latest_version

        return [
            entry.artefact
            for entry in self._entries
            if entry.group == group
            and entry.matches_version(version)
            and (artefact_type is None or entry.artefact_type == artefact_type)
        ]

    def get_all_facts_in_group(self, group: str, version: int | None = None):
        """Gets all facts in a group for the given format version (defaults to latest)."""
        return self.get_all_in_group(group, ArtefactType.FACT, version=version)

    def get_all_metrics_in_group(self, group: str, version: int | None = None):
        """Gets all metrics in a group for the given format version (defaults to latest)."""
        return self.get_all_in_group(group, ArtefactType.METRIC, version=version)

    @property
    def available_groups(self) -> set[str]:
        """Provides the set of available groups for the latest version."""
        return {
            entry.group
            for entry in self._entries
            if entry.matches_version(self.latest_version)
        }

    @property
    def all_available(self) -> list[str]:
        """Provides a list of all registered items for the latest version in 'group.name' format."""
        return [
            f"{entry.group}.{entry.name}"
            for entry in self._entries
            if entry.matches_version(self.latest_version)
        ]

    @property
    def available_facts(self) -> list[str]:
        """Provides a list of all available fact identifiers for the latest version."""
        return [
            f"{entry.group}.{entry.name}"
            for entry in self._entries
            if entry.matches_version(self.latest_version)
            and entry.artefact_type == ArtefactType.FACT
        ]

    @property
    def available_metrics(self) -> list[str]:
        """Provides a list of all available metric identifiers for the latest version."""
        return [
            f"{entry.group}.{entry.name}"
            for entry in self._entries
            if entry.matches_version(self.latest_version)
            and entry.artefact_type == ArtefactType.METRIC
        ]

    def get_facts(self, version: int | None = None) -> dict[str, Any]:
        """Dictionary mapping artefact names to their classes for the given version."""
        return {
            artefact.__artefact_name__: artefact
            for artefact in self.all_facts(version=version)
        }

    def get_metrics(self, version: int | None = None) -> dict[str, Any]:
        """Dictionary mapping metric names to their classes for the given version."""
        return {
            artefact.__artefact_name__: artefact
            for artefact in self.all_metrics(version=version)
        }


registry = _ArtefactRegistry()

##
## Decorators
##


def fact(
    *,
    group: str,
    name: str | None = None,
    metadata: ArtefactMetadata | None = None,
    min_version: int = 2,
    max_version: int | None = None,
):
    """
    Python decorator to register a fact class in the specified group and format version range.
    """

    def decorator(fact_cls):
        insert_pydantic_schema_proxy(fact_cls)

        actual_name = name or fact_cls.__name__

        registry.register(
            actual_name,
            group,
            fact_cls,
            artefact_type=ArtefactType.FACT,
            metadata=metadata,
            min_version=min_version,
            max_version=max_version,
        )
        return fact_cls

    return decorator


def metric(
    *,
    group: str,
    name: str | None = None,
    metadata: ArtefactMetadata | None = None,
    min_version: int = 2,
    max_version: int | None = None,
):
    """
    Python decorator to register a metric class in the specified group and format version range.
    """

    def decorator(metric_cls):
        insert_pydantic_schema_proxy(metric_cls)

        actual_name = name or metric_cls.__name__

        registry.register(
            actual_name,
            group,
            metric_cls,
            artefact_type=ArtefactType.METRIC,
            metadata=metadata,
            min_version=min_version,
            max_version=max_version,
        )
        return metric_cls

    return decorator
