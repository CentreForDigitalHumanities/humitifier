import dataclasses
from datetime import datetime
from typing import TypeVar

from django.template.loader import render_to_string
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe

from humitifier_common.artefacts.registry.registry import ArtefactType

T = TypeVar("T")


class ArtefactVisualizer:
    artefact: type[T] = None
    title: str | None = None
    template: str = "hosts/scan_visualizer/components/base_component.html"

    def __init__(self, artefact_data: T, scan_date: datetime):
        self.artefact_data = artefact_data
        self.scan_date = scan_date

    def show(self):
        return self.artefact_data is not None

    def get_context(self, **kwargs) -> dict:
        kwargs["title"] = self.title
        kwargs["is_metric"] = self.artefact.__artefact_type__ == ArtefactType.METRIC
        kwargs["alpinejs_settings"] = {}

        return kwargs

    def render(self) -> str | None:
        return render_to_string(self.template, context=self.get_context())


class ItemizedArtefactVisualizer(ArtefactVisualizer):
    template = "hosts/scan_visualizer/components/itemized_component.html"
    attributes: dict[str, str] | None = None

    def get_items(self) -> list[dict[str, str]]:
        data = []
        for item, label in self.attributes.items():
            value = self.get_attribute_value(item)
            data.append(
                {
                    "label": label,
                    "value": value,
                }
            )

        return data

    def get_context(self, **kwargs) -> dict:
        context = super().get_context(**kwargs)

        context["data"] = self.get_items()

        return context

    def get_attribute_value(self, item):
        value = getattr(self.artefact_data, item, None)

        if value and hasattr(self, f"get_{item}_display"):
            actual_value = getattr(self, f"get_{item}_display")(value)
            if actual_value is not None:
                return mark_safe(actual_value)

            return actual_value

        return value


@dataclasses.dataclass
class Bar:
    label_1: str
    label_2: str | None = None
    used: str | None = None
    total: str | None = None
    percentage: float | None = None


class BarsArtefactVisualizer(ArtefactVisualizer):
    template = "hosts/scan_visualizer/components/bars_component.html"

    def get_context(self, **kwargs) -> dict:
        context = super().get_context(**kwargs)

        context["data"] = self.get_bar_items()

        return context

    def get_bar_items(self) -> list[Bar]:
        raise NotImplementedError()


@dataclasses.dataclass
class Card:
    """
    Dataclass to represent a card.

    Title will be displayed promenently as the header
    Aside will be displayed next to the title, for secondary info

    Content can be specified in one of two ways, either as a string
    which will just be 'pasted' as the content, or a dict of key-values
    which will be displayed as a nicely formatted list. (Like ItemizedArtefactVisualizer)

    Search_value should be filled with a string that will be used to search through.
    (Using a simple 'string includes search-text' method).
    If multiple elements should be searched at the same time, you should just concat
    them inside the string ;)
    """

    title: str | None = None
    aside: str | None = None
    content: str | None = None
    content_items: dict[str, str] | None = None
    search_value: str | None = None


class SearchableCardsVisualizer(ArtefactVisualizer):
    template = "hosts/scan_visualizer/components/searchable_cards_component.html"
    search_placeholder = "Search"
    allow_search = True
    min_items_for_search = 3

    def get_items(self) -> list[Card]:
        raise NotImplementedError()

    @cached_property
    def _items(self):
        return self.get_items()

    def show_search(self):
        return self.allow_search and len(self._items) > self.min_items_for_search

    def get_context(self, **kwargs) -> dict:
        context = super().get_context(**kwargs)

        context["data"] = self._items
        context["show_search"] = self.show_search
        context["search_placeholder"] = self.search_placeholder

        context["alpinejs_settings"]["search"] = "''"

        return context
