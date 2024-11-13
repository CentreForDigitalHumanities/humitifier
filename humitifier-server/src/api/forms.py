from django import forms
from django.conf import settings

from api.models import OAuth2Application


class ScopeWidget(forms.CheckboxSelectMultiple):

    def format_value(self, value):
        if value is None:
            return []
        return value.split(",")

    def optgroups(self, name, value, attrs=None):
        self.choices = [
            (scope, scope) for scope in set(settings.OAUTH2_PROVIDER["SCOPES"].keys())
        ]

        return super().optgroups(name, value, attrs)


class OAuth2ApplicationForm(forms.ModelForm):
    class Meta:
        model = OAuth2Application
        fields = [
            "name",
            "client_id",
            "client_secret",
            "access_profile",
            "allowed_scopes",
        ]
        widgets = {
            "allowed_scopes": ScopeWidget,
        }
