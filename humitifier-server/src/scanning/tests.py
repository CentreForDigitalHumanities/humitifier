from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from humitifier_common.artefacts import registry

from scanning.forms import ScanSpecForm
from scanning.models import ScanSpec, ArtefactSpec

User = get_user_model()


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

    def test_ignore_older_version_only_artefacts(self):
        """Test that artefacts only present in older versions are ignored."""
        from pydantic import BaseModel

        class LegacyOnlyArtefact(BaseModel):
            old: str

        # Register an artefact only for version 1 (or max_version=1 when latest is 2)
        registry.register(
            "LegacyArtefact",
            "testgroup",
            LegacyOnlyArtefact,
            max_version=1,
        )

        spec = ScanSpec.objects.create(
            name="legacy_spec", artefact_groups=["testgroup"]
        )
        ArtefactSpec.objects.create(
            artefact_name="testgroup.LegacyArtefact",
            scan_spec=spec,
        )

        resolved = spec._build_artefact_scan_input()
        self.assertNotIn("testgroup.LegacyArtefact", resolved)

        artefact_spec = ArtefactSpec(
            artefact_name="testgroup.LegacyArtefact", scan_spec=spec
        )
        self.assertFalse(artefact_spec.is_valid_config)


class ScanSpecFormTestCase(TestCase):

    def test_form_initial_with_multiple_groups(self):
        spec = ScanSpec.objects.create(
            name="multi_group_spec",
            artefact_groups=["generic", "server"],
        )
        form = ScanSpecForm(instance=spec)
        rendered = form.as_p()

        # Both checkboxes should have checked attribute rendered
        self.assertIn('value="generic"\n    \n     id="id_artefact_groups_1" checked', rendered)
        self.assertIn('value="server"\n    \n     id="id_artefact_groups_3" checked', rendered)

        # In optgroups, generic and server should be marked selected
        bound_field = form["artefact_groups"]
        widget_data = bound_field.field.widget.get_context(
            "artefact_groups", bound_field.value(), {"id": "id_artefact_groups"}
        )
        selected_values = [
            opt["value"]
            for group, options, index in widget_data["widget"]["optgroups"]
            for opt in options
            if opt["selected"]
        ]
        self.assertEqual(sorted(selected_values), ["generic", "server"])

    def test_form_save_updates_artefact_groups(self):
        spec = ScanSpec.objects.create(
            name="test_spec",
            artefact_groups=["generic"],
        )
        data = {
            "name": "test_spec_updated",
            "artefact_groups": ["server", "special"],
        }
        form = ScanSpecForm(data=data, instance=spec)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.name, "test_spec_updated")
        self.assertEqual(sorted(saved.artefact_groups), ["server", "special"])

    def test_form_save_empty_artefact_groups(self):
        spec = ScanSpec.objects.create(
            name="test_spec",
            artefact_groups=["generic", "server"],
        )
        data = {
            "name": "test_spec_cleared",
        }
        form = ScanSpecForm(data=data, instance=spec)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.artefact_groups, [])


class ScanSpecViewsTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin", password="password", email="admin@example.com"
        )
        self.client.force_login(self.user)

    def test_edit_scan_spec_view_get_populates_checked_boxes(self):
        spec = ScanSpec.objects.create(
            name="multi_spec",
            artefact_groups=["generic", "server"],
        )
        url = reverse("scanning:edit_scan_spec", args=[spec.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")
        self.assertTrue('value="generic"' in content)
        self.assertTrue('value="server"' in content)
        # Verify both generic and server inputs are checked in the HTML response
        self.assertRegex(
            content,
            r'<input[^>]*value="generic"[^>]*checked',
        )
        self.assertRegex(
            content,
            r'<input[^>]*value="server"[^>]*checked',
        )
