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
