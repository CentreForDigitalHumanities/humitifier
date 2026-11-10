from datetime import datetime

from django.test import SimpleTestCase

from hosts.scan_visualizers.v3.artefact_visualizers import IPTablesVisualizer
from humitifier_common.artefacts import (
    IPTableRules,
    IPTables,
    IPTablesChain,
    IPTablesPortAccess,
    IPTablesPortAccessSource,
)


def _rule(**kwargs) -> IPTableRules:
    defaults = {
        "pkts": 0,
        "bytes": 0,
        "target": "ACCEPT",
        "prot": "tcp",
        "opt": None,
        "in": "*",
        "out": "*",
        "source": "0.0.0.0/0",
        "destination": "0.0.0.0/0",
        "options": "",
    }
    defaults.update(kwargs)
    return IPTableRules(**defaults)


class IPTableRulesSerializationTestCase(SimpleTestCase):
    def test_roundtrip_by_field_name(self):
        # The scanner dumps by field name ('in_'), the server validates that
        # again; both the alias and the field name should be accepted
        rule = _rule(**{"in": "eth0"})

        dumped = rule.model_dump(mode="json")
        self.assertEqual(dumped["in_"], "eth0")

        parsed = IPTableRules.model_validate(dumped)
        self.assertEqual(parsed.in_, "eth0")

        del dumped["in_"]
        parsed_by_alias = IPTableRules.model_validate({**dumped, "in": "lo"})
        self.assertEqual(parsed_by_alias.in_, "lo")


class IPTablesVisualizerTestCase(SimpleTestCase):
    def setUp(self):
        self.artefact = IPTables(
            chains=[
                IPTablesChain(
                    chain="INPUT",
                    default_policy="DROP",
                    rules=[
                        _rule(options="tcp dpt:80 state NEW"),
                        _rule(
                            source="131.211.0.0/16 (test.host)",
                            options="tcp dpt:22",
                        ),
                        _rule(**{"in": "lo"}, prot="all"),
                        _rule(target="DROP", source="10.0.0.0/8", options="tcp dpt:25"),
                        _rule(target="RATE_LIMIT", options="tcp dpt:443"),
                    ],
                ),
                IPTablesChain(chain="FORWARD", default_policy="ACCEPT", rules=[]),
                IPTablesChain(chain="OUTPUT", default_policy="ACCEPT", rules=[]),
                IPTablesChain(chain="RATE_LIMIT", rules=[]),
            ],
            port_access=[
                IPTablesPortAccess(
                    port=None, protocol="all", allowed_from=["0.0.0.0/0@lo"]
                ),
                IPTablesPortAccess(
                    port="22",
                    protocol="tcp",
                    allowed_from=[
                        IPTablesPortAccessSource(
                            source="131.211.194.250",
                            resolved_hostname="fs-ils-194.im.hum.uu.nl",
                        )
                    ],
                ),
                IPTablesPortAccess(
                    port="80",
                    protocol="tcp",
                    allowed_from=["0.0.0.0/0"],
                    default_open=True,
                ),
                IPTablesPortAccess(
                    port="25", protocol="tcp", denied_from=["10.0.0.0/8"]
                ),
                IPTablesPortAccess(
                    port="1000:2000", protocol="udp", allowed_from=["10.1.0.0/16"]
                ),
            ],
        )
        self.visualizer = IPTablesVisualizer(self.artefact, datetime.now())

    def test_not_shown_without_chains(self):
        visualizer = IPTablesVisualizer(IPTables(chains=[]), datetime.now())
        self.assertFalse(visualizer.show())

    def test_shown_with_chains(self):
        self.assertTrue(self.visualizer.show())

    def test_port_access(self):
        context = self.visualizer.get_context()

        self.assertEqual(context["open_to_all_count"], 1)

        by_port = {item["port"]: item for item in context["port_access"]}

        self.assertEqual(by_port["Any port"]["allowed_from"], ["anyone via lo"])
        self.assertEqual(by_port["80"]["allowed_from"], ["anyone"])
        self.assertEqual(by_port["25"]["denied_from"], ["10.0.0.0/8"])

        # Resolved hostname title check
        source_22 = by_port["22"]["allowed_from"][0]
        self.assertEqual(source_22.source, "131.211.194.250")
        self.assertEqual(source_22.title, "fs-ils-194.im.hum.uu.nl")

        # Port service check
        self.assertEqual(by_port["22"]["service"], "ssh")
        self.assertEqual(by_port["80"]["service"], "http")
        self.assertEqual(by_port["25"]["service"], "smtp")
        self.assertIsNone(by_port["Any port"]["service"])
        self.assertIsNone(by_port["1000\u20132000"]["service"])

        # Ranges get a nicer separator
        self.assertIn("1000\u20132000", by_port)

    def test_ip_sorting(self):
        artefact = IPTables(
            chains=[IPTablesChain(chain="INPUT", rules=[])],
            port_access=[
                IPTablesPortAccess(
                    port="443",
                    protocol="tcp",
                    allowed_from=[
                        "192.168.1.1",
                        "10.1.0.0/16",
                        "0.0.0.0/0@lo",
                        IPTablesPortAccessSource(
                            source="131.211.194.250",
                            resolved_hostname="fs-ils-194.im.hum.uu.nl",
                        ),
                        "10.0.0.0/8",
                    ],
                )
            ],
        )
        visualizer = IPTablesVisualizer(artefact, datetime.now())
        context = visualizer.get_context()
        allowed = context["port_access"][0]["allowed_from"]
        self.assertEqual(
            [str(s) for s in allowed],
            [
                "anyone via lo",
                "10.0.0.0/8",
                "10.1.0.0/16",
                "131.211.194.250",
                "192.168.1.1",
            ],
        )

    def test_chains_and_rules(self):
        context = self.visualizer.get_context()

        self.assertEqual(context["num_rules"], 5)
        self.assertEqual(len(context["chains"]), 4)

        input_rules = context["chains"][0]["rules"]
        self.assertEqual(input_rules[0]["target_color"], "green")
        self.assertEqual(input_rules[2]["in"], "lo")
        self.assertEqual(input_rules[3]["target_color"], "red")
        self.assertEqual(input_rules[4]["target_color"], "gray")
        self.assertIn("dpt:22", input_rules[1]["search_value"])
        self.assertEqual(input_rules[1]["source"], "131.211.0.0/16 (test.host)")

    def test_render(self):
        html = self.visualizer.render()

        self.assertIn("Port access", html)
        self.assertIn("anyone via lo", html)
        self.assertIn("5 rules", html)
        self.assertIn("in 4 chains", html)
        self.assertIn("RATE_LIMIT", html)
        self.assertIn('title="fs-ils-194.im.hum.uu.nl"', html)
        self.assertIn(">131.211.194.250</span>", html)
        self.assertIn("underline decoration-dotted underline-offset-2 cursor-help", html)
        self.assertIn("(ssh)", html)
        self.assertIn("(http)", html)
        self.assertIn("View rules", html)
        self.assertIn('x-show="show_rules"', html)
        self.assertIn("131.211.0.0/16 (test.host)", html)
