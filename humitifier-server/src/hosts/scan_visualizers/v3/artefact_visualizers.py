from django.utils.safestring import mark_safe

from hosts.scan_visualizers.base_components import ArtefactVisualizer
from hosts.templatetags.host_tags import uptime
from humitifier_common.artefacts import UptimeV3


class UptimeVisualizer(ArtefactVisualizer):
    title = "Host uptime"
    artefact = UptimeV3

    def get_context(self, **kwargs):
        context = super().get_context(**kwargs)

        artefact_data: UptimeV3 | None = self.artefact_data

        if not artefact_data:
            context["content"] = '<div class="text-gray-500">Unknown</div>'
        else:
            host_uptime = uptime(artefact_data.uptime, self.scan_date)

            context["content"] = mark_safe(
                f"<div class='flex align-center'" f">{host_uptime}</div>"
            )

        return context
