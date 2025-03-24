from django.template.loader import render_to_string

from hosts.scan_visualizers import ScanVisualizer


class EmptyVisualizer(ScanVisualizer):

    def get_context(self, **kwargs):
        kwargs.update(
            {
                "host": self.host,
            }
        )

        kwargs.update(self.provided_context)

        return kwargs


    def render(self):
        return render_to_string(
            "hosts/scan_visualizer/empty.html",
            context=self.get_context(),
            request=self.request,
        )