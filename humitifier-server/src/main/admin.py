from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_financial_operator",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
        (
            "Humitifier options",
            {
                "fields": (
                    "is_local_account",
                    "wild_wasteland_mode",
                    "default_home",
                    "access_profiles",
                ),
            },
        ),
    )
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_financial_operator",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_financial_operator",
        "is_active",
        "groups",
    )


# Register your models here.
admin.site.register(User, CustomUserAdmin)
