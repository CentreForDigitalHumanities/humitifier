from humitifier.props import PackageList
from humitifier.html import SearchInput
from humitifier.html.protocols import HtmlComponent


class PackageListFilter(list[PackageList]):

    def options(self) -> set[str]:
        return set((pkg.name for pgklist in self for pkg in pgklist))
    
    def component(self, html_cls: type[HtmlComponent]) -> HtmlComponent:
        match html_cls.__name__:
            case SearchInput.__name__:
                return SearchInput(
                    name=PackageList.alias,
                    label="Package",
                    options=self.options()
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")