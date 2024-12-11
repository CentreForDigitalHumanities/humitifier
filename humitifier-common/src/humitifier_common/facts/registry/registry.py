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
        self, name: str, namespace: str, fact, fact_type: FactType = FactType.FACT
    ):
        key = (name, namespace)
        if key in self._registry:
            raise ValueError(f"Fact {name} already registered in namespace {namespace}")

        self._registry[key] = fact

        # add meta-variable to the fact class
        fact.__fact_name__ = f"{namespace}.{name}"
        fact.__fact_type__ = fact_type

    def get(
        self, name: str, namespace: str | None = None, fact_type: FactType | None = None
    ):
        if namespace is None:
            if "." in name:
                namespace, name = name.split(".", 1)
                return self.get(name, namespace, fact_type)

            for key in self._registry:
                if key[0] == name:
                    item = self._registry[key]

                    # check if the fact type matches
                    # if not, the user requested the wrong type
                    if fact_type is not None and item.__fact_type__ != fact_type:
                        break

                    return item
        else:
            key = (name, namespace)
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

    def get_all_in_namespace(self, namespace: str, fact_type: FactType | None = None):
        items = [
            self._registry[(name, _namespace)]
            for name, _namespace in self._registry.keys()
            if _namespace == namespace
        ]

        if fact_type is None:
            return items

        return [item for item in items if item.__fact_type__ == fact_type]

    def get_all_facts_in_namespace(self, namespace: str):
        return self.get_all_in_namespace(namespace, FactType.FACT)

    def get_all_metrics_in_namespace(self, namespace: str):
        return self.get_all_in_namespace(namespace, FactType.METRIC)

    @property
    def all_namespaces(self):
        return {namespace for (_, namespace) in self._registry.keys()}

    @property
    def all_available(self):
        return [f"{namespace}.{name}" for name, namespace in self._registry.keys()]

    @property
    def available_facts(self):
        return [
            f"{namespace}.{name}"
            for (name, namespace), _fact in self._registry.items()
            if _fact.__fact_type__ == FactType.FACT
        ]

    @property
    def available_metrics(self):
        return [
            f"{namespace}.{name}"
            for (name, namespace), _fact in self._registry.items()
            if _fact.__fact_type__ == FactType.METRIC
        ]


registry = _FactsRegistry()

##
## Decorators
##


def fact(*, namespace: str, name: str | None = None):
    def decorator(fact_cls):
        actual_name = name or fact_cls.__name__
        registry.register(actual_name, namespace, fact_cls, fact_type=FactType.FACT)
        return fact_cls

    return decorator


def metric(*, namespace: str, name: str | None = None):
    def decorator(metric_cls):
        actual_name = name or metric_cls.__name__
        registry.register(actual_name, namespace, metric_cls, fact_type=FactType.METRIC)
        return metric_cls

    return decorator
