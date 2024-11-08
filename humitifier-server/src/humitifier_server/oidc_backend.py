from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class HumitifierOIDCAuthenticationBackend(OIDCAuthenticationBackend):

    def create_user(self, claims):
        email = claims.get('email')
        first_name = claims.get('given_name')
        last_name = claims.get('family_name')
        username = self.get_username(claims)

        return self.UserModel.objects.create_user(username, email=email,
                                            first_name=first_name, last_name=last_name)

    def filter_users_by_claims(self, claims):
        username = self.get_username(claims)
        if not username:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(username=username, is_local_account=False)

    def get_username(self, claims):
        return claims.get('preferred_username')

    def update_user(self, user, claims):
        email = claims.get('email')
        first_name = claims.get('given_name')
        last_name = claims.get('family_name')

        user.email = email
        user.first_name = first_name
        user.last_name = last_name

        user.save()

        return user