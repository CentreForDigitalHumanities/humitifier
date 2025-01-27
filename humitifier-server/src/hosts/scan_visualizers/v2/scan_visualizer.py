from hosts.scan_visualizers.base_components import ArtefactVisualizer

from hosts.scan_visualizers.base_visualizer import ComponentScanVisualizer

import hosts.scan_visualizers.v2.artefact_visualizers as visualizers


class V2ScanVisualizer(ComponentScanVisualizer):
    template = "hosts/scan_visualizer/v2.html"

    visualizers: list[type[ArtefactVisualizer]] = [
        visualizers.UptimeVisualizer,
        visualizers.BlocksVisualizer,
        visualizers.MemoryVisualizer,
        visualizers.ZFSVisualizer,
        visualizers.HardwareVisualizer,
        visualizers.HostMetaVisualizer,
        visualizers.HostMetaVHostsVisualizer,
        visualizers.HostnameCtlVisualizer,
        visualizers.PuppetAgentVisualizer,
        visualizers.IsWordpressVisualizer,
        visualizers.PackageListVisualizer,
        visualizers.UsersVisualizer,
        visualizers.GroupsVisualizer,
    ]

    static_data = {
        "data_source": "Data source",
        "has_tofu_config": "Has OpenTofu config",
        "otap_stage": "OTAP stage",
        "department": "Department",
        "customer": "Customer",
        "contact": "Contact",
    }

    def get_context(self, **kwargs):
        context = super().get_context(**kwargs)
        context["static_data"] = []

        for attr, label in self.static_data.items():
            context["static_data"].append(
                {
                    "label": label,
                    "value": getattr(self.host, attr, None),
                }
            )

        return context
