from humitifier.props import Purpose
from humitifier.html import SelectInput
from humitifier.html.protocols import HtmlComponent


class PurposeFilter(list[Purpose]):

    def options(self) -> set[str]:
        return set(self)
    
    def component(self, html_cls: type[HtmlComponent]) -> HtmlComponent:
        match html_cls.__name__:
            case SelectInput.__name__:
                return SelectInput(
                    name=Purpose.alias,
                    label="Purpose",
                    options=self.options()
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")