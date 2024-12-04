"""
This module contains code to build and manage the facts registry.
Used by agent/server to retrieve the facts dynamically.
"""

##
## Registry
##


class _FactsRegistry:

    def __init__(self):
        self._registry = {}

    def register(self, name: str, namespace: str, fact):
        key = (name, namespace)
        if key in self._registry:
            raise ValueError(f"Fact {name} already registered in namespace {namespace}")

        self._registry[key] = fact

        # add meta-variable to the fact class
        fact.__fact_name__ = f"{namespace}.{name}"

    def get(self, name: str, namespace: str | None = None):
        if namespace is None:
            if "." in name:
                namespace, name = name.split(".", 1)
                return self.get(name, namespace)

            for key in self._registry:
                if key[0] == name:
                    return self._registry[key]
        else:
            key = (name, namespace)
            return self._registry.get(key)

        return None

    def all(self):
        return self._registry.values()

    def get_all_in_namespace(self, namespace: str):
        return [
            self._registry[(name, _namespace)]
            for name, _namespace in self._registry.keys()
            if _namespace == namespace
        ]

    @property
    def available_facts(self):
        return [f"{namespace}.{name}" for name, namespace in self._registry.keys()]


registry = _FactsRegistry()

##
## Decorators
##


def fact(*, namespace: str, name: str | None = None):
    def decorator(fact_cls):
        actual_name = name or fact_cls.__name__
        registry.register(actual_name, namespace, fact_cls)
        return fact_cls

    return decorator
