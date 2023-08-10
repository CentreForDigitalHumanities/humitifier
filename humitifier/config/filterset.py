from humitifier.html import SelectInput, SearchInput
from humitifier.protocols import FilterProperty
from functools import cached_property

Component = SelectInput | SearchInput
FilterConfig = tuple[type[FilterProperty], Component]


class FiltersetConfig(list[FilterConfig]):
    
    @cached_property
    def kv(self) -> dict[str, type[FilterProperty]]:
        return {prop_cls.alias: prop_cls for prop_cls, _ in self}
    
    def __getitem__(self, key) -> FilterConfig:
        return self.kv[key]