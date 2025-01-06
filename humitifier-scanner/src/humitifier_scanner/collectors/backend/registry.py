from .collector import Collector

##
## Registry
##


class _FactImplementationRegistry:

    def __init__(self):
        self._registry = {}

    def register(self, fact_implementation: Collector):
        fact = fact_implementation._fact.__fact_name__
        variant = fact_implementation.variant
        key = (fact, variant)
        if key in self._registry:
            raise ValueError(f"Fact {fact} already registered with variant {variant}")

        self._registry[key] = fact_implementation

    def get(self, fact: str, variant: str | None = None):
        key = (fact, variant or "default")
        return self._registry.get(key)

    def all(self):
        return self._registry.values()

    @property
    def available_implementations(self):
        return [f"{fact}:{variant}" for fact, variant in self._registry.keys()]


registry = _FactImplementationRegistry()
