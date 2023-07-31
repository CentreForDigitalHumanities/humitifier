from humitifier.props import Hostname
from humitifier.html import SearchInput
from humitifier.html.protocols import HtmlComponent


class HostnameFilter(list[Hostname]):

    def options(self) -> set[str]:
        return set(self)
    
    def component(self, html_cls: type[HtmlComponent]) -> HtmlComponent:
        match html_cls.__name__:
            case SearchInput.__name__:
                return SearchInput(
                    name=Hostname.alias,
                    label="Hostname",
                    options=self.options()
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")