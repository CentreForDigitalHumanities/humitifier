from humitifier.models.host_state import HostState
from humitifier.facts.package_list import PackageList as PackageListFact
from humitifier.html import HtmlString, KvRow, InlineList

_HtmlComponent = KvRow | InlineList | HtmlString

class PackageList(PackageListFact):
    
    @classmethod
    def from_host_state(cls, host_state: HostState) -> "PackageList":
        out = host_state[PackageListFact.alias]
        return cls.from_stdout(out)
    
    def component(self, html_cls: type[_HtmlComponent]) -> _HtmlComponent:
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