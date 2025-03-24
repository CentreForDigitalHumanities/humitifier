from django.template.loader import render_to_string

from hosts.scan_visualizers.base_visualizer import ScanVisualizer


class V1ScanVisualizer(ScanVisualizer):
    """Legacy visualizer, simply pipes data into the old handcrafted templates"""

    def render(self):
        return render_to_string(
            "hosts/scan_visualizer/v1/v1.html",
            context=self.get_context(),
            request=self.request,
        )
