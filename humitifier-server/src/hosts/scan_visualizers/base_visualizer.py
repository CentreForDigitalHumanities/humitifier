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


class ComponentScanVisualizer(ScanVisualizer):
    template = None

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
    ) -> dict[str, str]:
        output = {}
        for component in components:
            data = self.get_artefact_data(component.artefact)
            if data:
                cmp = component(data, self.scan_data.scan_date)
                if cmp.show():
                    output[component.title] = cmp.render()

        return output

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

    def get_context(self, **kwargs):
        context = super().get_context(**kwargs)

        context["facts"] = self.render_components(self.fact_visualizers)
        context["metrics"] = self.render_components(self.metric_visualizers)

        return context
