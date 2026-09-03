from django import forms
from .models import Network

class NetworkForm(forms.ModelForm):
    class Meta:
        model = Network
        fields = ["name", "vlan", "cidr_range"]
