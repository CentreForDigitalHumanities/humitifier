from django import forms

from .models import DataSource


class DataSourceForm(forms.ModelForm):
    class Meta:
        model = DataSource
        fields = ["name", "identifier", "source_type"]
        widgets = {
            "source_type": forms.RadioSelect,
            "identifier": forms.TextInput(attrs={"disabled": True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # It's a disabled field, so it won't be sent to the server on submission
        # We're relying on auto-generated values anyway
        self.fields["identifier"].required = False

    def clean_identifier(self):
        # Should not happen?
        if "identifier" in self.cleaned_data and self.cleaned_data["identifier"]:
            return self.cleaned_data["identifier"]

        # Get the initial auto-generated value from data
        if "initial-identifier" in self.data:
            return self.data["initial-identifier"]

        return None
