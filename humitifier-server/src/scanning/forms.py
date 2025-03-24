from django import forms
from humitifier_common.artefacts import registry

from scanning.models import ArtefactSpec, ScanSpec


class ScanSpecCreateForm(forms.ModelForm):
    class Meta:
        model = ScanSpec
        fields = [
            "name",
            "parent",
        ]


class ScanSpecForm(forms.ModelForm):
    class Meta:
        model = ScanSpec
        fields = [
            "name",
            "parent",
            "artefact_groups",
        ]
        widgets = {
            "artefact_groups": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the options of artefact_groups to the value of registry.available_groups
        self.fields["artefact_groups"].widget.choices = [
            (group, group) for group in registry.available_groups
        ]
        self.fields["artefact_groups"].required = False


class ArtefactSpecForm(forms.ModelForm):
    class Meta:
        model = ArtefactSpec
        fields = [
            "artefact_name",
            "knockout",
            "scan_spec",
        ]
        widgets = {
            "artefact_name": forms.Select,
            "scan_spec": forms.HiddenInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Will be filled in during save
        self.fields["scan_spec"].required = False

        self.fields["artefact_name"].widget.choices = [(None, "---")] + [
            (artefact, artefact) for artefact in registry.all_available
        ]
