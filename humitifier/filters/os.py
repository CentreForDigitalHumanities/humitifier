from humitifier.props import Os
from humitifier.html import SelectInput
from humitifier.html.protocols import HtmlComponent


class OsFilter(list[Os]):

    def options(self) -> set[str]:
        return set(self)
    
    def component(self, html_cls: type[HtmlComponent]) -> HtmlComponent:
        match html_cls.__name__:
            case SelectInput.__name__:
                return SelectInput(
                    name=Os.alias,
                    label="Operating System",
                    options=self.options()
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")