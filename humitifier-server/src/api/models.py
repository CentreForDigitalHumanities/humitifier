from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from jsonschema.exceptions import ValidationError
from oauth2_provider.models import AbstractApplication


class OAuth2Application(AbstractApplication):
    access_profile = models.ForeignKey(
        "main.AccessProfile",
        on_delete=models.SET_NULL,
        related_name="oauth_applications",
        blank=True,
        null=True,
    )
    allowed_scopes = ArrayField(
        models.CharField(max_length=20),
    )

    def clean(self):
        super().clean()
        if self.allowed_scopes:
            allowed_scopes_set = set(self.allowed_scopes)
            available_scopes_set = set(settings.OAUTH2_PROVIDER["SCOPES"].keys())
            if not allowed_scopes_set.issubset(available_scopes_set):
                raise ValidationError("Invalid scopes in allowed_scopes")
