from humitifier.props import Owner
from humitifier.html import SearchInput
from humitifier.html.protocols import HtmlComponent


class OwnerFilter(list[Owner]):

    def options(self) -> set[str]:
        return set((owner.name for owner in self))
    
    def component(self, html_cls: type[HtmlComponent]) -> HtmlComponent:
        match html_cls.__name__:
            case SearchInput.__name__:
                return SearchInput(
                    name=Owner.alias,
                    label="Owner",
                    options=self.options()
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")