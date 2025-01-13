from hosts.models import ScanData


class ScanVisualizer:

    def __init__(self, scan_data: ScanData):
        self.scan_data = scan_data
        self.request = None

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
            }
        )

        return kwargs

    def render(self):
        raise NotImplementedError()
