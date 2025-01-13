from .collector import Collector

##
## Registry
##


class _CollectorRegistry:

    def __init__(self):
        self._registry = {}

    def register(self, collector: Collector):
        fact = collector.artefact_name()
        variant = collector.variant
        key = (fact, variant)
        if key in self._registry:
            raise ValueError(f"Fact {fact} already registered with variant {variant}")

        self._registry[key] = collector

    def get(self, fact: str, variant: str | None = None):
        key = (fact, variant or "default")
        return self._registry.get(key)

    def all(self):
        return self._registry.values()

    @property
    def available_implementations(self):
        return [f"{fact}:{variant}" for fact, variant in self._registry.keys()]


registry = _CollectorRegistry()
