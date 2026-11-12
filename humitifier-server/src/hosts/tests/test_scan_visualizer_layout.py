from datetime import datetime

from django.test import RequestFactory, TestCase

from hosts.models import Host, ScanData
import hosts.scan_visualizers.v2.artefact_visualizers as v2_visualizers
import hosts.scan_visualizers.v3.artefact_visualizers as v3_visualizers
from hosts.scan_visualizers.v2.scan_visualizer import V2ScanVisualizer
from hosts.scan_visualizers.v3.scan_visualizer import V3ScanVisualizer
from humitifier_common.artefacts import (
    Block,
    Blocks,
    DNS,
    DNSLookup,
    Hardware,
    HostnameCtl,
    Memory,
    MemoryRange,
    NetworkInterfaces,
    NetworkInterface,
    SELinux,
    Uptime,
    User,
    Users,
    V3Uptime,
)
from humitifier_common.scan_data import ScanInput, ScanOutput
from main.models import User as UserModel


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

    def test_category_metadata_on_visualizers(self):
        """
        Verify that artefact visualizers have their category attribute configured correctly.
        """
        self.assertEqual(v2_visualizers.HardwareVisualizer.category, "general")
        self.assertEqual(v2_visualizers.LshwVisualizer.category, "general")
        self.assertEqual(v2_visualizers.HostnameCtlVisualizer.category, "general")
        self.assertEqual(v2_visualizers.RebootPolicyVisualizer.category, "general")
        self.assertEqual(v2_visualizers.SELinuxVisualizer.category, "general")
        self.assertEqual(v2_visualizers.SystemdUnitsVisualizer.category, "software")
        self.assertEqual(v2_visualizers.NetworkInterfacesVisualizer.category, "network")
        self.assertEqual(v2_visualizers.DNSVisualizer.category, "network")
        self.assertEqual(v2_visualizers.WebserverVisualizer.category, "software")
        self.assertEqual(v2_visualizers.IsWordpressVisualizer.category, "web")
        self.assertEqual(v2_visualizers.PackageListVisualizer.category, "software")
        self.assertEqual(v2_visualizers.UsersVisualizer.category, "users")
        self.assertEqual(v2_visualizers.GroupsVisualizer.category, "users")
        self.assertEqual(v2_visualizers.PuppetAgentVisualizer.category, "automation")
        self.assertEqual(v2_visualizers.PyInfraReportVisualizer.category, "automation")
        self.assertEqual(v2_visualizers.HostMetaVisualizer.category, "metadata")

        self.assertEqual(v3_visualizers.IPTablesVisualizer.category, "network")
        self.assertEqual(v3_visualizers.PackageListVisualizer.category, "software")
        self.assertEqual(
            v3_visualizers.PackageManagerInfoVisualizer.category, "software"
        )
        self.assertEqual(v3_visualizers.DockerComposeVisualizer.category, "containers")
        self.assertEqual(v3_visualizers.DockerImageVisualizer.category, "containers")
        self.assertEqual(
            v3_visualizers.DockerContainerVisualizer.category, "containers"
        )

    def test_v3_get_fact_sections_and_slot_indexing(self):
        """
        Verify that get_fact_sections groups components by category and assigns
        deterministic slot index within each section.
        """
        user = User(
            name="alice",
            uid=1000,
            gid=1000,
            info="Alice",
            home="/home/alice",
            shell="/bin/bash",
        )
        dns = DNS(
            dns_lookups=[
                DNSLookup(
                    name="example.com",
                    a_records=["93.184.216.34"],
                    cname_records=[],
                )
            ]
        )
        hostname_ctl = HostnameCtl(
            hostname="server1",
            os="Ubuntu 24.04",
            cpe_os_name="ubuntu",
            kernel="6.8.0",
            virtualization="kvm",
        )

        scan_data = self._create_scan_data(
            facts={
                Users.__artefact_name__: [user.model_dump(mode="json")],
                DNS.__artefact_name__: dns.model_dump(mode="json"),
                HostnameCtl.__artefact_name__: hostname_ctl.model_dump(mode="json"),
            },
            version=3,
        )

        visualizer = V3ScanVisualizer(self.host, scan_data, {})
        sections = visualizer.get_artefact_sections()

        section_titles = [s.title for s in sections]
        self.assertIn("General", section_titles)
        self.assertIn("Network & Security", section_titles)
        self.assertIn("Users & Groups", section_titles)
        # Empty sections must be omitted
        self.assertNotIn("Hardware", section_titles)
        self.assertNotIn("Containers", section_titles)
        self.assertNotIn("Web", section_titles)

        os_section = next(s for s in sections if s.title == "General")
        self.assertEqual(len(os_section.components), 1)
        self.assertEqual(os_section.components[0].title, "Host metadata")

        network_section = next(s for s in sections if s.title == "Network & Security")
        self.assertEqual(len(network_section.components), 1)
        self.assertEqual(network_section.components[0].title, "DNS")
        # In categorized mode, components receive local sequential order_index starting at 0
        self.assertEqual(network_section.components[0].order_index, 0)

    def test_categorized_sections_assign_local_slot_indices(self):
        """
        Verify that sparse categorized sections assign consecutive local slot indices
        [0, 1, 2...] to maximize column utilization and prevent empty columns,
        while flat mode preserves static global slot indexing.
        """
        hardware = Hardware(
            num_cpus=4,
            memory=[
                MemoryRange(
                    range="0x0000000000000000-0x000000007fffffff",
                    size=2147483648,
                    state="online",
                    removable=False,
                    block="memory0",
                )
            ],
            block_devices=[],
            pci_devices=[],
            usb_devices=[],
            total_memory_gb=2,
        )
        hostname_ctl = HostnameCtl(
            hostname="server1",
            os="Ubuntu 24.04",
            cpe_os_name="ubuntu",
            kernel="6.8.0",
            virtualization="kvm",
        )
        selinux = SELinux(enabled=False, policy_name=None, mode=None)
        network_interfaces = [
            NetworkInterface(
                name="eth0",
                altnames=[],
                link_type="ether",
                mac_address="00:00:00:00:00:00",
                flags=["up"],
                addresses=[],
            ),
        ]
        dns = DNS(
            dns_lookups=[
                DNSLookup(
                    name="example.com",
                    a_records=["93.184.216.34"],
                    cname_records=[],
                )
            ]
        )

        # In V3 General category:
        # visualizers: [Hardware (0), Lshw (1), RebootPolicy (2), HostMeta (3), HostnameCtl (4), SELinux (5)]
        # We supply Hardware, HostnameCtl, and SELinux (3 non-consecutive visualizers).
        # In V3 Network & Security category:
        # visualizers: [NetworkInterfaces (0), IPTables (1), DNS (2)]
        # We supply NetworkInterfaces and DNS (2 non-consecutive visualizers).
        scan_data = self._create_scan_data(
            facts={
                Hardware.__artefact_name__: hardware.model_dump(mode="json"),
                HostnameCtl.__artefact_name__: hostname_ctl.model_dump(mode="json"),
                SELinux.__artefact_name__: selinux.model_dump(mode="json"),
                NetworkInterfaces.__artefact_name__: [
                    ni.model_dump(mode="json") for ni in network_interfaces
                ],
                DNS.__artefact_name__: dns.model_dump(mode="json"),
            },
            version=3,
        )

        visualizer = V3ScanVisualizer(self.host, scan_data, {})

        # 1. Categorized mode inspection
        sections = visualizer.get_artefact_sections()
        general_sec = next(s for s in sections if s.title == "General")
        self.assertEqual(len(general_sec.components), 3)
        self.assertEqual(
            [c.order_index for c in general_sec.components],
            [0, 1, 2],
        )

        network_sec = next(s for s in sections if s.title == "Network & Security")
        self.assertEqual(len(network_sec.components), 2)
        self.assertEqual(
            [c.order_index for c in network_sec.components],
            [0, 1],
        )

        # 2. Template rendering in categorized mode produces local data-slot-index values
        user_cat = UserModel.objects.create_user(
            username="sparse_cat_user",
            password="password",
            categorized_scan_visualizer=True,
        )
        factory = RequestFactory()
        req_cat = factory.get("/")
        req_cat.user = user_cat
        visualizer.request = req_cat
        html_cat = visualizer.render()

        # Check data-slot-index values exist sequentially
        self.assertIn('data-slot-index="0"', html_cat)
        self.assertIn('data-slot-index="1"', html_cat)
        self.assertIn('data-slot-index="2"', html_cat)

        # 3. Flat / non-categorized mode preserves static global indexing
        user_flat = UserModel.objects.create_user(
            username="sparse_flat_user",
            password="password",
            categorized_scan_visualizer=False,
        )
        req_flat = factory.get("/")
        req_flat.user = user_flat
        visualizer.request = req_flat
        ctx_flat = visualizer.get_context()
        flat_facts_sec = next(
            s for s in ctx_flat["artefact_sections"] if s.title == "Facts"
        )

        # Hardware is at static index 0 in fact_visualizers
        # HostnameCtl, SELinux, NetworkInterfaces, DNS have static indices in fact_visualizers
        fact_vis_titles = [v.title for v in visualizer.fact_visualizers]
        for cmp in flat_facts_sec.components:
            expected_static_index = fact_vis_titles.index(cmp.title)
            self.assertEqual(cmp.order_index, expected_static_index)

    def test_v3_context_categorized_preference(self):
        """
        Verify that V3ScanVisualizer checks user.categorized_scan_visualizer.
        """
        user_categorized = UserModel.objects.create_user(
            username="cat_user", password="password", categorized_scan_visualizer=True
        )
        user_flat = UserModel.objects.create_user(
            username="flat_user", password="password", categorized_scan_visualizer=False
        )

        scan_data = self._create_scan_data(
            facts={
                Users.__artefact_name__: [
                    User(
                        name="root",
                        uid=0,
                        gid=0,
                        info="root",
                        home="/root",
                        shell="/bin/bash",
                    ).model_dump(mode="json")
                ]
            },
            version=3,
        )

        factory = RequestFactory()

        # Categorized enabled
        request_cat = factory.get("/")
        request_cat.user = user_categorized
        visualizer_cat = V3ScanVisualizer(self.host, scan_data, {})
        visualizer_cat.request = request_cat
        ctx_cat = visualizer_cat.get_context()
        self.assertTrue(ctx_cat["categorized_scan_visualizer"])
        self.assertTrue(len(ctx_cat["artefact_sections"]) > 0)

        # Categorized disabled (flat mode)
        request_flat = factory.get("/")
        request_flat.user = user_flat
        visualizer_flat = V3ScanVisualizer(self.host, scan_data, {})
        visualizer_flat.request = request_flat
        ctx_flat = visualizer_flat.get_context()
        self.assertFalse(ctx_flat["categorized_scan_visualizer"])
        self.assertEqual(len(ctx_flat["artefact_sections"]), 2)
        self.assertEqual(ctx_flat["artefact_sections"][0].title, "Metrics")
        self.assertEqual(ctx_flat["artefact_sections"][1].title, "Facts")

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
        # Categorized view (default): Uptime and Memory receive local sequential slot indices 0 and 1
        html = visualizer.render()
        self.assertIn('data-slot-index="0"', html)
        self.assertIn('data-slot-index="1"', html)
        self.assertIn("stable-columns", html)
        self.assertIn("flex flex-col gap-3", html)

        # Flat view: non-categorized rendering preserves static global slot indices (0 and 2 for Uptime and Memory)
        user_flat = UserModel.objects.create_user(
            username="v2_flat_slot_user",
            password="password",
            categorized_scan_visualizer=False,
        )
        factory = RequestFactory()
        req_flat = factory.get("/")
        req_flat.user = user_flat
        visualizer.request = req_flat
        html_flat = visualizer.render()
        self.assertIn('data-slot-index="0"', html_flat)
        self.assertIn('data-slot-index="2"', html_flat)

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

    def test_v3_template_rendering_categorized_and_flat(self):
        """
        Verify that v3.html renders section headers when categorized mode is enabled,
        and renders a flat Facts header when categorized mode is disabled.
        """
        user = User(
            name="bob",
            uid=1001,
            gid=1001,
            info="Bob",
            home="/home/bob",
            shell="/bin/bash",
        )
        scan_data = self._create_scan_data(
            facts={
                Users.__artefact_name__: [user.model_dump(mode="json")],
            },
            version=3,
        )

        user_cat = UserModel.objects.create_user(
            username="v3_cat_user",
            password="password",
            categorized_scan_visualizer=True,
        )
        user_flat = UserModel.objects.create_user(
            username="v3_flat_user",
            password="password",
            categorized_scan_visualizer=False,
        )

        factory = RequestFactory()

        # Categorized view: renders section title "Users & Groups"
        req_cat = factory.get("/")
        req_cat.user = user_cat
        viz_cat = V3ScanVisualizer(self.host, scan_data, {})
        viz_cat.request = req_cat
        html_cat = viz_cat.render()
        self.assertIn("Users &amp; Groups", html_cat)
        self.assertIn("Search users &amp; groups", html_cat)
        self.assertIn("collapsed: false", html_cat)
        self.assertIn('@click="collapsed = !collapsed"', html_cat)
        self.assertIn('x-show="!collapsed"', html_cat)
        self.assertIn("toggle-layout", html_cat)
        self.assertIn("translate-x-4", html_cat)
        self.assertNotIn("Switch to Classic Facts Layout", html_cat)

        # Flat view: renders generic "Facts" title
        req_flat = factory.get("/")
        req_flat.user = user_flat
        viz_flat = V3ScanVisualizer(self.host, scan_data, {})
        viz_flat.request = req_flat
        html_flat = viz_flat.render()
        self.assertIn("Facts", html_flat)
        self.assertIn("Search facts", html_flat)
        self.assertIn("collapsed: false", html_flat)
        self.assertIn('@click="collapsed = !collapsed"', html_flat)
        self.assertIn('x-show="!collapsed"', html_flat)
        self.assertIn("toggle-layout", html_flat)
        self.assertIn("translate-x-0", html_flat)
        self.assertNotIn("Switch to Categorized Layout", html_flat)

    def test_toggle_visualizer_layout_view(self):
        """
        Verify that ToggleVisualizerLayoutView inverts user preference and redirects to host.
        """
        user = UserModel.objects.create_superuser(
            username="toggle_view_user",
            password="password",
            categorized_scan_visualizer=True,
        )
        self.client.force_login(user)

        toggle_url = f"/hosts/host/{self.host.fqdn}/toggle-layout/?scan=latest"
        response = self.client.get(toggle_url)

        user.refresh_from_db()
        self.assertFalse(user.categorized_scan_visualizer)
        self.assertRedirects(response, f"/hosts/host/{self.host.fqdn}/?scan=latest")

        # Toggle back
        response = self.client.get(toggle_url)
        user.refresh_from_db()
        self.assertTrue(user.categorized_scan_visualizer)
        self.assertRedirects(response, f"/hosts/host/{self.host.fqdn}/?scan=latest")

    def test_column_downsizing_template_classes_and_script(self):
        """
        Verify that template outputs downsized grid classes according to component count:
        - 1 component: grid-cols-1 without xl:grid-cols-2 or ultrawide:grid-cols-3
        - 2 components: grid-cols-1 xl:grid-cols-2 without ultrawide:grid-cols-3
        - 3+ components: grid-cols-1 xl:grid-cols-2 ultrawide:grid-cols-3
        Also verify that the distribution script contains the dynamic column count calculation
        and gridTemplateColumns styling.
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
        blocks = [
            Block(
                name="sda",
                size_mb=512000,
                used_mb=256000,
                available_mb=256000,
                use_percent=50,
                mount="/",
            )
        ]

        # 1. Single component section (1 metric)
        scan_data_1 = self._create_scan_data(
            metrics={
                Uptime.__artefact_name__: uptime,
            }
        )
        viz_1 = V2ScanVisualizer(self.host, scan_data_1, {})
        html_1 = viz_1.render()
        self.assertIn("stable-columns grid grid-cols-1 items-start gap-3 px-2", html_1)
        self.assertNotIn("grid-cols-1 xl:grid-cols-2", html_1)
        self.assertNotIn("ultrawide:grid-cols-3", html_1)

        # 2. Dual component section (2 metrics)
        scan_data_2 = self._create_scan_data(
            metrics={
                Uptime.__artefact_name__: uptime,
                Memory.__artefact_name__: memory.model_dump(mode="json"),
            }
        )
        viz_2 = V2ScanVisualizer(self.host, scan_data_2, {})
        html_2 = viz_2.render()
        self.assertIn(
            "stable-columns grid grid-cols-1 xl:grid-cols-2 items-start gap-3 px-2",
            html_2,
        )
        self.assertNotIn("ultrawide:grid-cols-3", html_2)

        # 3. Multi component section (3 metrics)
        scan_data_3 = self._create_scan_data(
            metrics={
                Uptime.__artefact_name__: uptime,
                Blocks.__artefact_name__: [b.model_dump(mode="json") for b in blocks],
                Memory.__artefact_name__: memory.model_dump(mode="json"),
            }
        )
        viz_3 = V2ScanVisualizer(self.host, scan_data_3, {})
        html_3 = viz_3.render()
        self.assertIn(
            "stable-columns grid grid-cols-1 xl:grid-cols-2 ultrawide:grid-cols-3 items-start gap-3 px-2",
            html_3,
        )

        # 4. Distribution script verification
        self.assertIn("Math.min(items.length, getColumnCount()) || 1", html_3)
        self.assertIn("container.style.gridTemplateColumns =", html_3)
        self.assertIn("slotIndex % columnCount", html_3)

    def test_v3_categorized_column_downsizing(self):
        """
        Verify column downsizing in V3 categorized mode across multiple category sections.
        """
        uptime = V3Uptime(
            uptime=864000.0,
            since=datetime(2026, 11, 1, 0, 0, 0),
        )
        user = User(
            name="bob",
            uid=1001,
            gid=1001,
            info="Bob",
            home="/home/bob",
            shell="/bin/bash",
        )
        scan_data = self._create_scan_data(
            metrics={
                V3Uptime.__artefact_name__: uptime.model_dump(mode="json"),
            },
            facts={
                Users.__artefact_name__: [user.model_dump(mode="json")],
            },
            version=3,
        )
        user_cat = UserModel.objects.create_user(
            username="v3_downsize_user",
            password="password",
            categorized_scan_visualizer=True,
        )
        factory = RequestFactory()
        req = factory.get("/")
        req.user = user_cat

        viz = V3ScanVisualizer(self.host, scan_data, {})
        viz.request = req
        html = viz.render()

        # Both General (Uptime) and Users & Groups (Users) sections have 1 component each
        self.assertIn("stable-columns grid grid-cols-1 items-start gap-3 px-2", html)
        self.assertNotIn("xl:grid-cols-2", html)
        self.assertNotIn("ultrawide:grid-cols-3", html)
