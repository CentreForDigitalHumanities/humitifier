from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class HumitifierOIDCAuthenticationBackend(OIDCAuthenticationBackend):

    def create_user(self, claims):
        email = self.get_email(claims)
        first_name = claims.get("given_name")
        last_name = claims.get("family_name")
        username = self.get_username(claims)

        return self.UserModel.objects.create_user(
            username, email=email, first_name=first_name, last_name=last_name
        )

    def filter_users_by_claims(self, claims):
        username = self.get_username(claims)
        if not username:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(
            username__iexact=username, is_local_account=False
        )

    def get_username(self, claims):
        return claims.get("preferred_username").lower()

    def get_email(self, claims):
        email = claims.get("email")

        # The UU OIDC provider is out-of-spec and can return a list of emails
        # instead of just the one as the spec specifies.
        # So, we just pick the first one we find.
        if isinstance(email, list):
            if len(email) > 0:
                return email[0]
            else:
                return None

        return email

    def update_user(self, user, claims):
        email = self.get_email(claims)
        first_name = claims.get("given_name")
        last_name = claims.get("family_name")

        user.username = self.get_username(claims)
        user.email = email
        user.first_name = first_name
        user.last_name = last_name

        user.save()

        return user
