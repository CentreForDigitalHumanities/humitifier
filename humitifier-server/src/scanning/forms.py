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
    artefact_groups = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = ScanSpec
        fields = [
            "name",
            "parent",
            "artefact_groups",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the options of artefact_groups to the value of registry.available_groups
        available_groups = set(registry.available_groups)
        if self.instance and self.instance.artefact_groups:
            available_groups.update(self.instance.artefact_groups)
        self.fields["artefact_groups"].choices = [
            (group, group) for group in sorted(available_groups)
        ]


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
