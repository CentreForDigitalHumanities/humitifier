"""
This module contains code to build and manage the facts registry.
Used by agent/server to retrieve the facts dynamically.
"""

from enum import Enum


##
## Registry
##


class FactType(Enum):
    FACT = "fact"
    METRIC = "metric"


class _FactsRegistry:

    def __init__(self):
        self._registry = {}

    def register(
        self, name: str, group: str, fact, fact_type: FactType = FactType.FACT
    ):
        key = (name, namespace)
        key = (name, group)
        if key in self._registry:
            raise ValueError(f"Fact {name} already registered in group {group}")

        self._registry[key] = fact

        # add meta-variable to the fact class
        fact.__fact_name__ = f"{group}.{name}"
        fact.__fact_type__ = fact_type

    def get(
        self, name: str, group: str | None = None, fact_type: FactType | None = None
    ):
        if group is None:
            if "." in name:
                group, name = name.split(".", 1)
                return self.get(name, group, fact_type)

            for key in self._registry:
                if key[0] == name:
                    item = self._registry[key]

                    # check if the fact type matches
                    # if not, the user requested the wrong type
                    if fact_type is not None and item.__fact_type__ != fact_type:
                        break

                    return item
        else:
            key = (name, group)
            item = self._registry.get(key)

            # check if the fact type matches
            # if not, the user requested the wrong type
            if fact_type is None or item.__fact_type__ == fact_type:
                return item

        return None

    def all(self, fact_type: FactType | None = None):
        if fact_type is not None:
            return [
                fact
                for fact in self._registry.values()
                if fact.__fact_type__ == fact_type
            ]

        return self._registry.values()

    def all_facts(self):
        return self.all(FactType.FACT)

    def all_metrics(self):
        return self.all(FactType.METRIC)

    def get_all_in_group(self, group: str, fact_type: FactType | None = None):
        items = [
            self._registry[(name, _group)]
            for name, _group in self._registry.keys()
            if _group == group
        ]

        if fact_type is None:
            return items

        return [item for item in items if item.__fact_type__ == fact_type]

    def get_all_facts_in_group(self, group: str):
        return self.get_all_in_group(group, FactType.FACT)

    def get_all_metrics_in_group(self, group: str):
        return self.get_all_in_group(group, FactType.METRIC)

    @property
    def available_groups(self):
        return {group for (_, group) in self._registry.keys()}

    @property
    def all_available(self):
        return [f"{group}.{name}" for name, group in self._registry.keys()]

    @property
    def available_facts(self):
        return [
            f"{group}.{name}"
            for (name, group), _fact in self._registry.items()
            if _fact.__fact_type__ == FactType.FACT
        ]

    @property
    def available_metrics(self):
        return [
            f"{group}.{name}"
            for (name, group), _fact in self._registry.items()
            if _fact.__fact_type__ == FactType.METRIC
        ]


registry = _FactsRegistry()

##
## Decorators
##


def fact(*, group: str, name: str | None = None):
    def decorator(fact_cls):
        actual_name = name or fact_cls.__name__
        registry.register(actual_name, group, fact_cls, fact_type=FactType.FACT)
        return fact_cls

    return decorator


def metric(*, group: str, name: str | None = None):
    def decorator(metric_cls):
        actual_name = name or metric_cls.__name__
        registry.register(actual_name, group, metric_cls, fact_type=FactType.METRIC)
        return metric_cls

    return decorator
