from django.urls import reverse
from django.utils.safestring import mark_safe

from main.easy_tables import (
    BooleanColumn,
    BaseTable,
    ButtonColumn,
    CompoundColumn,
    MethodColumn,
    ValueColumn,
)
from main.models import AccessProfile, User


class UsersTable(BaseTable):
    class Meta:
        model = User
        columns = [
            "username",
            "full_name",
            "email",
            "access_profiles",
            "is_active",
            "is_local_account",
            "actions",
        ]
        column_type_overrides = {
            "is_active": BooleanColumn,
            "is_local_account": BooleanColumn(
                yes_no_values={True: "Local", False: "Solis", None: "Unknown"}
            ),
        }
        column_breakpoint_overrides = {
            "full_name": "lg",
            "email": "md",
            "is_active": "xl",
            "is_local_account": "2xl",
            "access_profiles": "sm",
        }
        no_data_message = "No users found. Please check your filters."
        no_data_message_wild_wasteland = (
            "It's lonely in here... Where did all the users go?"
        )

    full_name = ValueColumn("Name", value_attr="get_full_name")

    actions = CompoundColumn(
        "Actions",
        columns=[
            ButtonColumn(
                text="Edit",
                button_class="btn light:btn-primary dark:btn-outline mr-2",
                url=lambda obj: reverse("main:edit_user", args=[obj.pk]),
            ),
            ButtonColumn(
                text=lambda obj: "Disable" if obj.is_active else "Enable",
                button_class="btn btn-danger mr-2",
                url=lambda obj: reverse("main:deactivate_user", args=[obj.pk]),
            ),
            ButtonColumn(
                text="Change Password",
                button_class="btn btn-outline",
                url=lambda obj: reverse("main:user_change_password", args=[obj.pk]),
                show_check_function=lambda obj: obj.is_local_account,
            ),
        ],
    )

    # M2M fields are not supported by easy_tables, so let's use a MethodColumn
    access_profiles = MethodColumn("Access Profiles", method_name="get_access_profiles")

    @staticmethod
    def get_access_profiles(obj: User):
        if obj.is_superuser:
            return mark_safe("<span class='text-gray-500'>Superuser</span")

        if obj.access_profiles.exists():
            return ", ".join([profile.name for profile in obj.access_profiles.all()])

        return mark_safe("<span class='text-gray-500'>None</span")


class AccessProfilesTable(BaseTable):
    class Meta:
        model = AccessProfile
        columns = [
            "name",
            "description",
            "departments",
            "data_sources",
            "actions",
        ]
        no_data_message = "No access profiles found. Please check your filters."
        no_data_message_wild_wasteland = (
            "There are no access profiles here! "
            "Stop looking! There's nothing to see!"
        )

    actions = CompoundColumn(
        "Actions",
        columns=[
            ButtonColumn(
                text="Edit",
                button_class="btn light:btn-primary dark:btn-outline mr-2",
                url=lambda obj: reverse("main:edit_access_profile", args=[obj.pk]),
            ),
            ButtonColumn(
                text="Delete",
                button_class="btn btn-danger",
                url=lambda obj: reverse("main:delete_access_profile", args=[obj.pk]),
            ),
        ],
    )

    data_sources = MethodColumn("Data sources", method_name="get_data_sources")

    @staticmethod
    def get_data_sources(obj: AccessProfile):
        return ", ".join(obj.data_sources.values_list("name", flat=True))
