from django import forms

from .models import DataSource


class DataSourceForm(forms.ModelForm):
    class Meta:
        model = DataSource
        fields = ["name", "source_type"]
        widgets = {
            "source_type": forms.RadioSelect,
        }
