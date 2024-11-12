from oauth2_provider.scopes import SettingsScopes


class OAuth2Scopes(SettingsScopes):
    """Custom scopes backend, used to limit the scopes available to an application."""

    def get_available_scopes(self, application=None, request=None, *args, **kwargs):
        if application is None:
            return []

        return application.allowed_scopes

    def get_default_scopes(self, application=None, request=None, *args, **kwargs):
        if application is None:
            return []
        return application.allowed_scopes