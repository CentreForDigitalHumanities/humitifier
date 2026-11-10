from datetime import datetime

from django.test import TestCase

from hosts.models import Host, ScanData
from hosts.scan_visualizers.v2.scan_visualizer import V2ScanVisualizer
from hosts.scan_visualizers.v3.scan_visualizer import V3ScanVisualizer
from humitifier_common.artefacts import (
    Memory,
    Uptime,
    User,
    Users,
    V3Uptime,
)
from humitifier_common.scan_data import ScanInput, ScanOutput


class ScanVisualizerLayoutTestCase(TestCase):
    def setUp(self):
        self.host = Host.objects.create(fqdn="test-host.example.com")
        self.scan_date = datetime(2026, 11, 10, 12, 0, 0)

    def _create_scan_data(
        self, metrics: dict | None = None, facts: dict | None = None, version: int = 2
    ) -> ScanData:
        scan_output = ScanOutput(
            version=version,
            scan_date=self.scan_date,
            hostname=self.host.fqdn,
            original_input=ScanInput(hostname=self.host.fqdn, artefacts={}),
            metrics=metrics or {},
            facts=facts or {},
        )
        return ScanData(
            version=version,
            scan_date=self.scan_date,
            raw_data=scan_output.model_dump(mode="json"),
        )

    def test_render_components_structure_and_deterministic_order_index(self):
        """
        Verify that render_components returns structured dicts with title, content,
        and deterministic static order_index.
        """
        # Full scan data containing Uptime, Memory, and Users
        uptime = 864000.0
        memory = Memory(
            total_mb=16384,
            used_mb=6144,
            free_mb=10240,
            swap_total_mb=2048,
            swap_used_mb=0,
            swap_free_mb=2048,
        )
        user = User(
            name="root",
            uid=0,
            gid=0,
            info="root",
            home="/root",
            shell="/bin/bash",
        )

        scan_data_full = self._create_scan_data(
            metrics={
                Uptime.__artefact_name__: uptime,
                Memory.__artefact_name__: memory.model_dump(mode="json"),
            },
            facts={
                Users.__artefact_name__: [user.model_dump(mode="json")],
            },
        )

        visualizer_full = V2ScanVisualizer(self.host, scan_data_full, {})
        rendered_metrics = visualizer_full.render_components(
            visualizer_full.metric_visualizers
        )
        rendered_facts = visualizer_full.render_components(
            visualizer_full.fact_visualizers
        )

        # In V2ScanVisualizer:
        # metric_visualizers: [Uptime (idx 0), Blocks (idx 1), Memory (idx 2), ZFS (idx 3)]
        uptime_item = next(
            item for item in rendered_metrics if item.title == "Host uptime"
        )
        memory_item = next(
            item for item in rendered_metrics if item.title == "Memory usage"
        )
        self.assertEqual(uptime_item.order_index, 0)
        self.assertEqual(memory_item.order_index, 2)

        # fact_visualizers: Users is at a fixed static index in fact_visualizers
        users_item = next(item for item in rendered_facts if item.title == "Users")
        users_static_idx = [v.title for v in visualizer_full.fact_visualizers].index(
            "Users"
        )
        self.assertEqual(users_item.order_index, users_static_idx)

    def test_multi_host_consistency_with_missing_artefacts(self):
        """
        Verify that when a host is missing preceding artefacts (e.g. Uptime is missing),
        the remaining artefacts (e.g. Memory) still receive the exact same static order_index.
        """
        memory = Memory(
            total_mb=16384,
            used_mb=6144,
            free_mb=10240,
            swap_total_mb=2048,
            swap_used_mb=0,
            swap_free_mb=2048,
        )

        # Host 2 has only Memory (Uptime and Blocks are missing)
        scan_data_partial = self._create_scan_data(
            metrics={
                Memory.__artefact_name__: memory.model_dump(mode="json"),
            }
        )

        visualizer_partial = V2ScanVisualizer(self.host, scan_data_partial, {})
        rendered_metrics = visualizer_partial.render_components(
            visualizer_partial.metric_visualizers
        )

        self.assertEqual(len(rendered_metrics), 1)
        self.assertEqual(rendered_metrics[0].title, "Memory usage")
        self.assertEqual(rendered_metrics[0].order_index, 2)

    def test_template_rendering_data_slot_index(self):
        """
        Verify that V2/V3 template renders data-slot-index attributes matching order_index.
        """
        uptime = 864000.0
        memory = Memory(
            total_mb=16384,
            used_mb=6144,
            free_mb=10240,
            swap_total_mb=2048,
            swap_used_mb=0,
            swap_free_mb=2048,
        )

        scan_data = self._create_scan_data(
            metrics={
                Uptime.__artefact_name__: uptime,
                Memory.__artefact_name__: memory.model_dump(mode="json"),
            }
        )

        visualizer = V2ScanVisualizer(self.host, scan_data, {})
        html = visualizer.render()

        self.assertIn('data-slot-index="0"', html)
        self.assertIn('data-slot-index="2"', html)
        self.assertIn("stable-columns", html)
        self.assertIn("flex flex-col gap-3", html)

    def test_v3_visualizer_deterministic_slots(self):
        """
        Verify that V3ScanVisualizer also renders deterministic slots properly.
        """
        uptime = V3Uptime(
            uptime=864000.0,
            since=datetime(2026, 11, 1, 0, 0, 0),
        )
        scan_data = self._create_scan_data(
            metrics={
                V3Uptime.__artefact_name__: uptime.model_dump(mode="json"),
            },
            version=3,
        )

        visualizer = V3ScanVisualizer(self.host, scan_data, {})
        html = visualizer.render()

        self.assertIn('data-slot-index="0"', html)
        self.assertIn("Visualizer version: 3", html)
