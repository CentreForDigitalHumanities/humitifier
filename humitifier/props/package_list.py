from humitifier.facts.package_list import PackageList as PackageListFact
from humitifier.html import HtmlString, KvRow, InlineList

from typing import TypeVar

_Component = TypeVar("_Component", HtmlString, KvRow, InlineList)


class PackageList(PackageListFact):

    @staticmethod
    def query_option_set(items=list["PackageList"]) -> set[str]:
        return set(pkg.name for host_pkgs in items for pkg in host_pkgs)
    
    @classmethod
    def from_host_state(cls, host_state) -> "PackageList":
        return cls(host_state[PackageListFact])
    
    def component(self, html_cls: type[_Component]) -> _Component:
        match html_cls.__name__:
            case KvRow.__name__:
                return KvRow(
                    label="Packages", 
                    value=self.component(InlineList)
                )
            case InlineList.__name__:
                items = [HtmlString(f"{pkg.name}=={pkg.version}") for pkg in self]
                return InlineList(items)
            case HtmlString.__name__:
                return HtmlString(f"{len(self)} packages installed")
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")
    
    def filter(self, query: str) -> bool:
        return any(query in pkg.name for pkg in self)