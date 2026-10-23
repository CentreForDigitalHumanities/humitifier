import json

from django import forms

from .models import DataSource, DataSourceType, Host, OperatingSystem, SavedSearch
from .search import parse_column


class DataSourceForm(forms.ModelForm):
    class Meta:
        model = DataSource
        fields = [
            "name",
            "identifier",
            "source_type",
            "scan_scheduling",
            "default_scan_spec",
        ]
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


class OperatingSystemForm(forms.ModelForm):
    class Meta:
        model = OperatingSystem
        fields = [
            "name",
            "outdated",
        ]


class HostScanSpecForm(forms.ModelForm):
    class Meta:
        model = Host
        fields = (
            "scan_spec_override",
        )


class HostForm(forms.ModelForm):
    class Meta:
        model = Host
        fields = (
            "fqdn",
            "data_source",
            "scan_spec_override",
            "has_tofu_config",
            "otap_stage",
            "billable",
            "department",
            "customer",
            "contact",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_source"].queryset = DataSource.objects.filter(
            source_type=DataSourceType.MANUAL
        )  # Example condition


class SavedSearchForm(forms.ModelForm):
    columns = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = SavedSearch
        fields = (
            "title",
            "description",
            "query",
            "columns",
            "show_matches",
            "is_public",
        )
        widgets = {
            "query": forms.Textarea(attrs={"rows": 3}),
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(self.initial.get("columns"), list):
            self.initial["columns"] = json.dumps(self.initial["columns"])
        elif self.instance and isinstance(self.instance.columns, list):
            self.initial["columns"] = json.dumps(self.instance.columns)

    def clean_columns(self):
        data = self.cleaned_data.get("columns", "")
        if not data:
            return []

        if isinstance(data, list):
            raw_cols = data
        else:
            try:
                parsed = json.loads(data)
                if isinstance(parsed, list):
                    raw_cols = parsed
                else:
                    raw_cols = [c.strip() for c in str(data).split(",") if c.strip()]
            except (json.JSONDecodeError, TypeError):
                raw_cols = [c.strip() for c in str(data).split(",") if c.strip()]

        validated_cols = []
        for raw in raw_cols:
            col_str = str(raw).strip()
            if not col_str:
                continue
            try:
                parse_column(col_str)
            except ValueError as e:
                raise forms.ValidationError(f"Invalid column expression '{col_str}': {e}")
            validated_cols.append(col_str)

        return validated_cols


