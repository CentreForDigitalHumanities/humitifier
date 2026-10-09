from hosts.scan_visualizers import V2ScanVisualizer

import hosts.scan_visualizers.v2.artefact_visualizers as v2_visualizers
import hosts.scan_visualizers.v3.artefact_visualizers as v3_visualizers
from hosts.scan_visualizers.base_components import ArtefactVisualizer


class V3ScanVisualizer(V2ScanVisualizer):
    # We inherit most from the v2 visualizer, as the v3 format is not that different.

    VERSION = 3

    visualizers: list[type[ArtefactVisualizer]] = [
        v3_visualizers.UptimeVisualizer,
        v2_visualizers.BlocksVisualizer,
        v2_visualizers.MemoryVisualizer,
        v2_visualizers.ZFSVisualizer,
        v2_visualizers.HardwareVisualizer,
        v2_visualizers.LshwVisualizer,
        v2_visualizers.RebootPolicyVisualizer,
        v2_visualizers.NetworkInterfacesVisualizer,
        v3_visualizers.IPTablesVisualizer,
        v2_visualizers.DNSVisualizer,
        v2_visualizers.HostMetaVisualizer,
        v2_visualizers.WebserverVisualizer,
        v2_visualizers.HostnameCtlVisualizer,
        v2_visualizers.PuppetAgentVisualizer,
        v2_visualizers.PyInfraReportVisualizer,
        v2_visualizers.IsWordpressVisualizer,
        v2_visualizers.SELinuxVisualizer,
        v3_visualizers.PackageListVisualizer,
        v3_visualizers.PackageManagerInfoVisualizer,
        v2_visualizers.UsersVisualizer,
        v2_visualizers.GroupsVisualizer,
        v2_visualizers.SystemdUnitsVisualizer,
    ]
