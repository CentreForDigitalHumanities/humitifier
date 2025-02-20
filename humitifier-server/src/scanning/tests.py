from django.test import TestCase
from humitifier_common.artefacts import registry

from scanning.models import ScanSpec, ArtefactSpec


class ScanInputBuildingTestCase(TestCase):

    def setUp(self):
        self.scanspec = ScanSpec.objects.create(
            name="test", artefact_groups=["generic"]
        )

    def test_simple(self):
        """Test if we get a output with the same amount of artefacts as are in the
        group
        """
        self.assertEqual(self.scanspec.artefact_groups, ["generic"])

        resolved_scan_artefacts = self.scanspec._build_artefact_scan_input()

        self.assertEqual(
            len(resolved_scan_artefacts.items()),
            len(registry.get_all_in_group("generic")),
        )

    def test_extra_artefact(self):
        """Test if adding a artefact of a different group works"""
        ArtefactSpec.objects.create(
            artefact_name=registry.get_all_in_group("server")[0].__artefact_name__,
            scan_spec=self.scanspec,
        )

        resolved_scan_artefacts = self.scanspec._build_artefact_scan_input()

        self.assertEqual(
            len(resolved_scan_artefacts.items()),
            len(registry.get_all_in_group("generic")) + 1,
        )

    def test_override_artefact(self):
        """Test if adding a artefact of a different group works"""
        overriden_artefact = registry.get_all_in_group("generic")[0]
        ArtefactSpec.objects.create(
            artefact_name=overriden_artefact.__artefact_name__,
            scan_spec=self.scanspec,
            _scan_options={"variant": "test"},
        )

        resolved_scan_artefacts = self.scanspec._build_artefact_scan_input()

        self.assertEqual(
            len(resolved_scan_artefacts.items()),
            len(registry.get_all_in_group("generic")),
        )

        self.assertEqual(
            resolved_scan_artefacts[overriden_artefact.__artefact_name__].variant,
            "test",
        )

    def test_knockout_artefact(self):
        """Test if knocking out an artefact works"""
        ArtefactSpec.objects.create(
            artefact_name=registry.get_all_in_group("generic")[0].__artefact_name__,
            scan_spec=self.scanspec,
            knockout=True,
        )

        resolved_scan_artefacts = self.scanspec._build_artefact_scan_input()

        self.assertEqual(
            len(resolved_scan_artefacts.items()),
            len(registry.get_all_in_group("generic")) - 1,
        )

    def test_inheritance(self):
        """Test if inheritance from parent works"""
        scanspec2 = ScanSpec.objects.create(
            name="child", artefact_groups=[], parent=self.scanspec
        )

        ArtefactSpec.objects.create(
            artefact_name=registry.get_all_in_group("server")[0].__artefact_name__,
            scan_spec=scanspec2,
        )

        resolved_scan_artefacts = scanspec2._build_artefact_scan_input()

        self.assertEqual(
            len(resolved_scan_artefacts.items()),
            len(registry.get_all_in_group("generic")) + 1,
        )

    def test_multiple_inheritance(self):
        # Create the first child
        scanspec2 = ScanSpec.objects.create(
            name="child", artefact_groups=[], parent=self.scanspec
        )

        # Add the first server artefact to that child
        ArtefactSpec.objects.create(
            artefact_name=registry.get_all_in_group("server")[0].__artefact_name__,
            scan_spec=scanspec2,
        )

        # Create the second child
        scanspec3 = ScanSpec.objects.create(
            name="child-2", artefact_groups=[], parent=scanspec2
        )

        # Add a different artefact to that child
        ArtefactSpec.objects.create(
            artefact_name=registry.get_all_in_group("server")[1].__artefact_name__,
            scan_spec=scanspec3,
        )

        resolved_scan_artefacts = scanspec3._build_artefact_scan_input()

        # We should have 2 more than in the generic group
        self.assertEqual(
            len(resolved_scan_artefacts.items()),
            len(registry.get_all_in_group("generic")) + 2,
        )

    def test_multiple_inheritance_knockout(self):
        """Test if inheritance from parent works with knockout

        This tests if adding an extra artefact, and then knocking it back out
        in a subsequent child-scan-spec works
        """
        # Create the first child
        scanspec2 = ScanSpec.objects.create(
            name="child", artefact_groups=[], parent=self.scanspec
        )

        # Add the first server artefact to that child
        ArtefactSpec.objects.create(
            artefact_name=registry.get_all_in_group("server")[0].__artefact_name__,
            scan_spec=scanspec2,
        )

        # Create the second child
        scanspec3 = ScanSpec.objects.create(
            name="child-2", artefact_groups=[], parent=scanspec2
        )

        # Add the same artefact as in scanspec2, but with a knockout flag now
        ArtefactSpec.objects.create(
            artefact_name=registry.get_all_in_group("server")[0].__artefact_name__,
            scan_spec=scanspec3,
            knockout=True,
        )

        resolved_scan_artefacts = scanspec3._build_artefact_scan_input()

        # We should be back to the same amount of artefacts as are in generic
        self.assertEqual(
            len(resolved_scan_artefacts.items()),
            len(registry.get_all_in_group("generic")),
        )
