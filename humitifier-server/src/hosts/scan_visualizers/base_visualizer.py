from dataclasses import dataclass
from typing import Any

from django.template.loader import render_to_string

from hosts.models import Host, ScanData
from hosts.scan_visualizers.base_components import ArtefactVisualizer
from humitifier_common.artefacts.registry.registry import ArtefactType


class ScanVisualizer:

    def __init__(self, host: Host, scan_data: ScanData, context: dict):
        self.host = host
        self.scan_data = scan_data
        self.request = None
        self.provided_context = context

    def get_context(self, **kwargs):
        kwargs.update(
            {
                "current_scan_date": self.scan_data.scan_date,
                "scan_data": (
                    self.scan_data.parsed_data
                    if self.scan_data.version > 1
                    else self.scan_data.raw_data
                ),
                "raw_data": self.scan_data.raw_data,
                "host": self.host,
            }
        )

        kwargs.update(self.provided_context)

        return kwargs

    def render(self):
        raise NotImplementedError()


@dataclass
class _Component:
    title: str
    content: str
    order_index: int
    category: str = "general"


@dataclass
class _Section:
    title: str
    slug: str
    components: list[_Component]


@dataclass
class _Category:
    id: str
    title: str


class ComponentScanVisualizer(ScanVisualizer):
    template = None

    VERSION: int | None = None

    CATEGORIES: list[_Category] = [
        _Category("metrics", "Metrics"),
        _Category("general", "General"),
        _Category("hardware", "Hardware"),
        _Category("os", "Operating System"),
        _Category("automation", "Automation & Config"),
        _Category("network", "Network & Security"),
        _Category("software", "Packages & Software"),
        _Category("containers", "Containers"),
        _Category("users", "Users & Groups"),
    ]

    visualizers: list[type[ArtefactVisualizer]] = []

    def render(self):
        return render_to_string(
            self.template,
            context=self.get_context(),
            request=self.request,
        )

    def get_artefact_data(self, artefact):
        artefact_name = artefact.__artefact_name__
        artefact_type: ArtefactType = artefact.__artefact_type__

        if artefact_type == ArtefactType.FACT:
            return self.scan_data.parsed_data.facts.get(artefact_name, None)
        else:
            return self.scan_data.parsed_data.metrics.get(artefact_name, None)

    def render_components(
        self, components: list[type[ArtefactVisualizer]]
    ) -> list[_Component]:
        output = []
        for index, component in enumerate(components):
            data = self.get_artefact_data(component.artefact)
            if data:
                cmp = component(data, self.scan_data.scan_date)
                if cmp.show():
                    output.append(
                        _Component(
                            title=component.title,
                            content=cmp.render() or "Something went wrong",
                            order_index=index,
                            category=getattr(component, "category", "general"),
                        )
                    )

        return output

    def get_artefact_sections(self) -> list[_Section]:
        sections = []

        seen_categories = set()
        for category in self.CATEGORIES:
            seen_categories.add(category.id)
            cat_visualizers = [
                v
                for v in self.visualizers
                if getattr(v, "category", "general") == category.id
            ]
            if not cat_visualizers:
                continue

            components = []
            for visualizer in cat_visualizers:
                data = self.get_artefact_data(visualizer.artefact)
                if data:
                    cmp = visualizer(data, self.scan_data.scan_date)
                    if cmp.show():
                        components.append(
                            _Component(
                                title=visualizer.title,
                                content=cmp.render() or "Something went wrong",
                                order_index=len(components),
                                category=category.id,
                            )
                        )
            if components:
                sections.append(
                    _Section(
                        title=category.title, slug=category.id, components=components
                    )
                )

        return sections

    @property
    def fact_visualizers(self):
        return [
            visualizer
            for visualizer in self.visualizers
            if visualizer.artefact.__artefact_type__ == ArtefactType.FACT
        ]

    @property
    def metric_visualizers(self):
        return [
            visualizer
            for visualizer in self.visualizers
            if visualizer.artefact.__artefact_type__ == ArtefactType.METRIC
        ]

    def _categorized_visualizer_enabled(self) -> bool:
        if self.request is None:
            return True

        # Should never be None....
        user = getattr(self.request, "user", None)
        if user is None or not user.is_authenticated:
            return True

        return user.categorized_scan_visualizer

    def get_context(self, **kwargs):
        context = super().get_context(**kwargs)

        context["visualizer_version"] = self.VERSION
        context["scan_format_version"] = self.scan_data.version

        categorized = self._categorized_visualizer_enabled()
        context["categorized_scan_visualizer"] = categorized
        if categorized:
            context["artefact_sections"] = self.get_artefact_sections()
        else:
            facts = self.render_components(self.fact_visualizers)
            metrics = self.render_components(self.metric_visualizers)

            context["artefact_sections"] = [
                _Section(title="Metrics", slug="metrics", components=metrics),
                _Section(title="Facts", slug="facts", components=facts),
            ]

        return context
