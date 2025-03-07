"""
This module contains code to build and manage the facts registry.
Used by agent/server to retrieve the facts dynamically.
"""

from dataclasses import dataclass
from enum import Enum


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


class _ArtefactRegistry:
    """
    Class to manage the registration and retrieval of facts and metrics (artefacts).

    This class serves as a registry to store, organize, and manage facts and metrics.
    Facts and metrics can be categorized by group, and the class provides
    utility functions to retrieve, list, and filter them based on their type or group.

    :ivar _registry: Internal storage for registered facts and metrics. It maps
        tuples of (name, group) to their respective fact or metric objects.
    :type _registry: dict[tuple[str, str], Any]
    """

    def __init__(self):
        self._registry = {}

    def register(
        self,
        name: str,
        group: str,
        artefact,
        artefact_type: ArtefactType = ArtefactType.FACT,
        metadata: ArtefactMetadata | None = None,
    ):
        """
        Registers a fact in the internal registry for a given group and name. Ensures that
        each fact is uniquely identified within the group. If a fact with the provided name
        and group is already registered, raises an error. This method also appends metadata
        to the fact object, including its fully qualified name and fact type. The method aims
        to manage fact type objects systematically.

        :param name: The name of the fact to register. A unique identifier within the group.
        :type name: str
        :param group: The group under which the fact is registered. Facilitates grouping.
        :type group: str
        :param artefact: The fact object to be associated with the registry entry.
        :type artefact: Any
        :param artefact_type: The type classification of the fact, defaulting to FactType.FACT.
        :type artefact_type: ArtefactType
        :param metadata:
        :type metadata: ArtefactMetadata
        :return: None
        :raises ValueError: If a fact with the given name and group is already registered.
        """
        key = (name, group)
        if key in self._registry:
            raise ValueError(f"Fact {name} already registered in group {group}")

        self._registry[key] = artefact

        # add meta-variable to the artefact class
        artefact.__artefact_name__ = f"{group}.{name}"
        artefact.__artefact_type__ = artefact_type
        artefact.__artefact_metadata__ = metadata or ArtefactMetadata()

    def get(
        self,
        name: str,
        group: str | None = None,
        artefact_type: ArtefactType | None = None,
    ):
        """
        Retrieve an item from the registry based on the provided name, group, and fact type.
        This function searches for a matching item in the registry. If the group is not
        specified and the name contains a ".", it tries to split it into name and group.
        The function also ensures that the returned item matches the provided fact type,
        if specified. If no matching item is found, it returns None.

        Usage:
        registry.get('ExampleFact', group='chicken')
        or:
        registry.get('chicken.ExampleFact')

        :param name: Name of the item to be retrieved.
        :type name: str
        :param group: Optional. Group the item belongs to. If None, the function attempts
                      to determine the group by processing the name.
        :type group: Union[str, None]
        :param artefact_type: Optional. Type of fact the item should match. If None, the
                          fact type is not checked.
        :type artefact_type: Union[FactType, None]
        :return: The item from the registry if a match is found, otherwise None.
        :rtype: Optional[Any]
        """
        if group is None:
            if "." in name:
                group, name = name.split(".", 1)
                return self.get(name, group, artefact_type)

            for key in self._registry:
                if key[0] == name:
                    item = self._registry[key]

                    # check if the artefact type matches
                    # if not, the user requested the wrong type
                    if (
                        artefact_type is not None
                        and item.__artefact_type__ != artefact_type
                    ):
                        break

                    return item
        else:
            key = (name, group)
            item = self._registry.get(key)

            # check if the fact type matches
            # if not, the user requested the wrong type
            if artefact_type is None or item.__fact_type__ == artefact_type:
                return item

        return None

    def all(self, artefact_type: ArtefactType | None = None):
        """
        Retrieve all artefacts from the registry. If a specific artefact type is provided,
        filters the results based on the artefact type.

        :param artefact_type: The specific type of facts to filter by. If None, returns all
            registered facts.
        :returns: A list of facts filtered by the provided type if specified, otherwise
            all facts from the registry.
        """
        if artefact_type is not None:
            return [
                artefact
                for artefact in self._registry.values()
                if artefact.__artefact_type__ == artefact_type
            ]

        return self._registry.values()

    def all_facts(self):
        """
        Retrieves all the facts from the registry.

        This method queries the internal data store and collects all items marked as
        `FactType.FACT`, returning them as a list.

        :return: A list of all stored facts marked as `FactType.FACT`.
        :rtype: list
        """
        return self.all(ArtefactType.FACT)

    def all_metrics(self):
        """
        Retrieves all the metrics from the registry.

        This method gathers and returns all entries that are categorized under the FactType
        of METRIC from the respective underlying data structure.

        :return: A collection of all facts identified as METRIC.
        :rtype: list or generator
        """
        return self.all(ArtefactType.METRIC)

    def get_all_in_group(self, group: str, artefact_type: ArtefactType | None = None):
        """
        Retrieve all items in a given group, optionally filtered by fact type.

        This method searches within the internal registry for all items matching
        the provided group. If a specific fact type is provided, the method
        further filters the items to return those with the specified fact type.

        :param group: The name of the group to retrieve items from.
        :type group: str
        :param artefact_type: Optional; specifies the fact type to filter the results.
        :type artefact_type: ArtefactType | None
        :return: A list of items belonging to the specified group, potentially
            filtered by the provided fact type.
        :rtype: list
        """
        items = [
            self._registry[(name, _group)]
            for name, _group in self._registry.keys()
            if _group == group
        ]

        if artefact_type is None:
            return items

        return [item for item in items if item.__artefact_type__ == artefact_type]

    def get_all_facts_in_group(self, group: str):
        """
        Gets all facts in the specified group.

        This method retrieves all entries categorized as facts from
        the given group. It internally utilizes the `get_all_in_group`
        function to filter and return entries of type `FactType.FACT`.
        The function aims to simplify fact extraction operations by
        group input.

        :param group: The name of the group whose facts are to be retrieved.
        :type group: str
        :return: A list of facts found within the specified group.
        :rtype: list
        """
        return self.get_all_in_group(group, ArtefactType.FACT)

    def get_all_metrics_in_group(self, group: str):
        """
        Retrieves all metrics associated with a specified group.

        This function is responsible for fetching all metrics that are
        categorized under the provided group. It ensures that only metrics
        are retrieved by enforcing the group and type parameters internally.

        :param group: A string representing the identifier of the group
                      whose metrics are to be retrieved.
        :type group: str
        :return: A list of metrics belonging to the specified group,
                 filtered by the metric type.
        :rtype: List
        """
        return self.get_all_in_group(group, ArtefactType.METRIC)

    @property
    def available_groups(self):
        """
        Provides the set of all available groups from the registry.

        This property scans the internal registry and retrieves all unique groups
        present in the registry.

        :return: A set containing the unique groups available in the registry.
        :rtype: set
        """
        return {group for (_, group) in self._registry.keys()}

    @property
    def all_available(self):
        """
        Provides a property to get a list of all available registered items
        in the registry. The items are returned in '{group}.{name}' format.

        :return: A list of strings where each string represents an item in the
            format 'group.name'.
        :rtype: list
        """
        return [f"{group}.{name}" for name, group in self._registry.keys()]

    @property
    def available_facts(self):
        """
        Provides a property to retrieve a list of all available facts from the internal
        registry. The property traverses through the registry, identifies entries marked
        as `FactType.FACT`, and formats them as `"<group>.<name>"`.

        :return: A list of available fact identifiers formatted as strings in the
            pattern "<group>.<name>" for all registered fact entries of type `FactType.FACT`.
        :rtype: list[str]
        """
        return [
            f"{group}.{name}"
            for (name, group), _fact in self._registry.items()
            if _fact.__artefact_type__ == ArtefactType.FACT
        ]

    @property
    def available_metrics(self):
        """
        Provides a property that returns a list of all available metric names in the
        format "group.name". This list is constructed by iterating over a registry
        of fact objects and filtering by those that are of FactType.METRIC.

        :return: List of metric names in the format "group.name".
        :rtype: list of str
        """
        return [
            f"{group}.{name}"
            for (name, group), _fact in self._registry.items()
            if _fact.__artefact_type__ == ArtefactType.METRIC
        ]


registry = _ArtefactRegistry()

##
## Decorators
##


def fact(
    *, group: str, name: str | None = None, metadata: ArtefactMetadata | None = None
):
    """
    Python decorator to register a fact class in the specified group. The function
    takes a fact class as input and registers it in a central registry for future
    use. Users can optionally provide a custom name for the fact; otherwise,
    the class name is used as the default.

    :param group: The category or group the fact belongs to.
    :type group: str
    :param name: Optional specific name to associate with the fact. Defaults to the
        class name of the fact if not provided.
    :type name: str | None
    :param metadata:
    :type metadata: ArtefactMetadata | None
    :return: A decorator function that registers the given class as a fact with the
        specified group and name in the fact registry.
    :rtype: Callable[[Type[object]], Type[object]]
    """

    def decorator(fact_cls):
        actual_name = name or fact_cls.__name__

        registry.register(
            actual_name,
            group,
            fact_cls,
            artefact_type=ArtefactType.FACT,
            metadata=metadata,
        )
        return fact_cls

    return decorator


def metric(
    *, group: str, name: str | None = None, metadata: ArtefactMetadata | None = None
):
    """
    Python decorator to register a metric class in the specified group. The function
    takes a metric class as input and registers it in a central registry for future
    use. Users can optionally provide a custom name for the metric; otherwise,
    the class name is used as the default.

    :param group: The group under which the metric class should be registered.
      This helps in categorizing and organizing the metrics.
    :type group: str
    :param name: An optional custom name for the metric. If not provided, the
      metric class name will be used as the default.
    :type name: str | None
    :param metadata:
    :type metadata: ArtefactMetadata | None
    :return: A decorator function that registers the given metric class when
      called. It ensures the metric class is associated with its group and name.
    :rtype: Callable[[Type], Type]
    """

    def decorator(metric_cls):
        actual_name = name or metric_cls.__name__

        registry.register(
            actual_name,
            group,
            metric_cls,
            artefact_type=ArtefactType.METRIC,
            metadata=metadata,
        )
        return metric_cls

    return decorator
