from django.urls import reverse

from api.models import OAuth2Application
from main.easy_tables import BaseTable, ButtonColumn, CompoundColumn, MethodColumn


class OAuth2ApplicationsTable(BaseTable):
    class Meta:
        model = OAuth2Application
        columns = [
            "name",
            "client_id",
            "access_profile",
            "allowed_scopes",
            "actions",
        ]
        column_breakpoint_overrides = {
            "client_id": "md",
            "access_profile": "md",
            "allowed_scopes": "2xl",
        }
        no_data_message = "No OAuth applications found. Please check your filters."
        no_data_message_wild_wasteland = (
            "No apps found... What is an Application anyway?"
        )

    allowed_scopes = MethodColumn("Allowed scopes", method_name="get_allowed_scopes")

    @staticmethod
    def get_allowed_scopes(obj: OAuth2Application):
        return ", ".join(obj.allowed_scopes)

    actions = CompoundColumn(
        "Actions",
        columns=[
            ButtonColumn(
                text="Edit",
                button_class="btn light:btn-primary dark:btn-outline mr-2",
                url=lambda obj: reverse("api:edit_oauth_application", args=[obj.pk]),
            ),
            ButtonColumn(
                text="Delete",
                button_class="btn btn-danger",
                url=lambda obj: reverse("api:delete_oauth_application", args=[obj.pk]),
            ),
        ],
    )
