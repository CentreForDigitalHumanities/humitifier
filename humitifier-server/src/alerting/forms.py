from django import forms

from alerting.models import AlertAcknowledgment


class AlertAcknowledgmentForm(forms.ModelForm):
    class Meta:
        model = AlertAcknowledgment
        fields = (
            "acknowledged_by",
            "reason",
            "persistent",
            "_alert",
            "host",
            "_creator",
            "custom_identifier",
        )
        widgets = {
            "_alert": forms.HiddenInput,
            "host": forms.HiddenInput,
            "_creator": forms.HiddenInput,
            "custom_identifier": forms.HiddenInput,
        }
