from .base_visualizer import ScanVisualizer
from .v1 import V1ScanVisualizer
from .v2 import V2ScanVisualizer
from ..models import Host, ScanData


def get_scan_visualizer(
    host: Host, scan_data: ScanData, context: dict
) -> ScanVisualizer:
    match scan_data.version:
        case 1:
            return V1ScanVisualizer(host, scan_data, context)
        case _:
            return V2ScanVisualizer(host, scan_data, context)
