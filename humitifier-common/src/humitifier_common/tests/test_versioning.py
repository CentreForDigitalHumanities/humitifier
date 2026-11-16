import unittest
from datetime import datetime
from pydantic import BaseModel, ValidationError

from humitifier_common.artefacts.registry.registry import (
    _ArtefactRegistry,
    ArtefactType,
    fact,
    metric,
)
from humitifier_common.scan_data import (
    ScanInput,
    ScanOutput,
    get_scan_output_class,
)


class TestArtefactRegistryVersioning(unittest.TestCase):

    def setUp(self):
        self.registry = _ArtefactRegistry()

    def test_version_registration_and_retrieval(self):
        class V2Fact(BaseModel):
            old_field: str

        class V3Fact(BaseModel):
            new_field: str
            subfield: int

        class V2OnlyFact(BaseModel):
            legacy_data: str

        class SharedFact(BaseModel):
            common_data: str

        # Register V2 version and V3 version of generic.CustomFact
        self.registry.register(
            "CustomFact", "generic", V2Fact, ArtefactType.FACT, max_version=2
        )
        self.registry.register(
            "CustomFact", "generic", V3Fact, ArtefactType.FACT, min_version=3
        )

        # Register V2-only fact
        self.registry.register(
            "OldFact", "generic", V2OnlyFact, ArtefactType.FACT, max_version=2
        )

        # Register shared fact (since v2, unbounded)
        self.registry.register(
            "SharedFact", "generic", SharedFact, ArtefactType.FACT, min_version=2
        )

        self.assertEqual(self.registry.latest_version, 3)
        self.assertEqual(self.registry.supported_versions, [2, 3])

        # Version 2 lookups
        self.assertIs(self.registry.get("generic.CustomFact", version=2), V2Fact)
        self.assertIs(self.registry.get("generic.OldFact", version=2), V2OnlyFact)
        self.assertIs(self.registry.get("generic.SharedFact", version=2), SharedFact)

        # Version 3 lookups (default version is 3)
        self.assertIs(self.registry.get("generic.CustomFact"), V3Fact)
        self.assertIs(self.registry.get("generic.CustomFact", version=3), V3Fact)
        self.assertIsNone(self.registry.get("generic.OldFact", version=3))
        self.assertIs(self.registry.get("generic.SharedFact", version=3), SharedFact)

        # Available facts (only latest version)
        self.assertIn("generic.CustomFact", self.registry.available_facts)
        self.assertIn("generic.SharedFact", self.registry.available_facts)
        self.assertNotIn("generic.OldFact", self.registry.available_facts)

    def test_overlapping_version_error(self):
        class FactA(BaseModel):
            val: str

        class FactB(BaseModel):
            val: str

        self.registry.register("Fact", "grp", FactA, min_version=2, max_version=4)
        with self.assertRaises(ValueError):
            self.registry.register("Fact", "grp", FactB, min_version=3, max_version=5)


class TestScanOutputVersioning(unittest.TestCase):

    def test_scan_output_v2_validation(self):
        # ScanOutput with V2 payload
        v2_raw = {
            "version": 2,
            "scan_date": datetime.now().isoformat(),
            "hostname": "server01.example.com",
            "original_input": {
                "hostname": "server01.example.com",
                "artefacts": {},
            },
            "facts": {
                "generic.HostnameCtl": {
                    "hostname": "web01",
                    "os": "Ubuntu 22.04.3 LTS",
                    "cpe_os_name": "cpe:/o:canonical:ubuntu_linux:22.04",
                    "kernel": "Linux 5.15.0-89-generic",
                    "virtualization": "kvm",
                }
            },
            "metrics": {},
            "errors": [],
        }

        output_v2 = ScanOutput.model_validate(v2_raw)
        self.assertEqual(output_v2.version, 2)
        self.assertEqual(output_v2.facts["generic.HostnameCtl"].hostname, "web01")
        self.assertEqual(
            output_v2.get_artefact_data("generic.HostnameCtl").os, "Ubuntu 22.04.3 LTS"
        )

    def test_get_scan_output_class(self):
        v2_cls = get_scan_output_class(2)
        self.assertEqual(v2_cls.__name__, "ScanOutputV2")
        v3_cls = get_scan_output_class(3)
        self.assertEqual(v3_cls.__name__, "ScanOutputV3")


if __name__ == "__main__":
    unittest.main()
