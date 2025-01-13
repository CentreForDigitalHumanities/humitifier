from .base_visualizer import ScanVisualizer
from .v1 import V1ScanVisualizer
from .v2 import V2ScanVisualizer
from ..models import ScanData


def get_scan_visualizer(scan_data: ScanData) -> ScanVisualizer:
    match scan_data.version:
        case 1:
            return V1ScanVisualizer(scan_data)
        case _:
            return V2ScanVisualizer(scan_data)
