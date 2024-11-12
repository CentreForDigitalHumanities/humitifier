from oauth2_provider.models import AccessToken
from rest_framework import permissions


class TokenHasApplication(permissions.BasePermission):
    def has_permission(self, request, view):
        token = request.auth
        if not token:
            return False

        try:
            access_token = AccessToken.objects.get(token=token)
            request.application = access_token.application
            return True
        except AccessToken.DoesNotExist:
            return False