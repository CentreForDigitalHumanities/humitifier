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


@dataclasses.dataclass
class TreeNode:
    """
    Dataclass to represent a single node of a tree.

    Title will be displayed as the label of the node. Badge is a small pill
    right after the title, for a short classification (e.g. a device class).
    Aside is displayed right-aligned and muted, for a short at-a-glance value
    (e.g. a disk size).

    Content works the same as it does for Card; either a plain string or a
    dict of key-values. It is shown in the shared detail panel when the node
    is selected, so the tree itself stays readable.

    Children are the nodes hanging below this one; they are rendered nested
    and can be collapsed.

    Search_value should be filled with a string that will be used to search
    through. A node is shown if either itself or any of its children match.

    Key uniquely identifies the node within its tree; it is assigned by the
    TreeVisualizer and used to track selection and expansion client-side.
    """

    title: str | None = None
    badge: str | None = None
    aside: str | None = None
    content: str | None = None
    content_items: dict[str, str] | None = None
    search_value: str | None = None
    children: list["TreeNode"] = dataclasses.field(default_factory=list)
    key: str | None = None

    @property
    def subtree_search_value(self) -> str:
        """The search value of this node and all of its children."""
        values = [self.search_value or ""]
        values += [child.subtree_search_value for child in self.children]

        return " ".join(values)


class TreeVisualizer(ArtefactVisualizer):
    template = "hosts/scan_visualizer/components/tree_component.html"
    search_placeholder = "Search"
    allow_search = True
    min_nodes_for_search = 3
    # Nodes up to (and including) this depth start out expanded; anything
    # deeper is collapsed, as trees tend to get quite large
    initially_expanded_depth = 1

    def get_nodes(self) -> list[TreeNode]:
        raise NotImplementedError()

    @cached_property
    def _nodes(self):
        return self.get_nodes()

    def _count_nodes(self, nodes: list[TreeNode]) -> int:
        return len(nodes) + sum(self._count_nodes(node.children) for node in nodes)

    def show_search(self):
        node_count = self._count_nodes(self._nodes)

        return self.allow_search and node_count > self.min_nodes_for_search

    @classmethod
    def _assign_keys(cls, nodes: list[TreeNode], prefix: str) -> None:
        for index, node in enumerate(nodes):
            node.key = f"{prefix}{index}"
            cls._assign_keys(node.children, f"{node.key}-")

    def get_context(self, **kwargs) -> dict:
        context = super().get_context(**kwargs)

        self._assign_keys(self._nodes, "n")

        context["data"] = self._nodes
        context["show_search"] = self.show_search
        context["search_placeholder"] = self.search_placeholder
        context["initially_expanded_depth"] = self.initially_expanded_depth
        # Everything searchable in one string, so the template can tell when
        # a search comes up completely empty
        context["search_haystack"] = " ".join(
            node.subtree_search_value for node in self._nodes
        ).lower()

        context["alpinejs_settings"]["search"] = "''"

        return context


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
