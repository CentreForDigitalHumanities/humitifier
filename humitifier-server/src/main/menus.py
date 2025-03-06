from django.urls import reverse
from simple_menu import Menu, MenuItem

from main.menu_item import HumitifierMenuItem

Menu.add_item(
    "main",
    MenuItem(
        "Dashboard",
        reverse("main:dashboard"),
        weight=1,
        icon="icons/dashboard.html",
        check=lambda request: request.user.is_authenticated,
    ),
)

Menu.add_item(
    "main",
    HumitifierMenuItem(
        "Auth",
        None,
        weight=20,
        icon="icons/users-alt.html",
        check=lambda request: request.user.is_superuser,
        children=[
            HumitifierMenuItem(
                "Users",
                reverse("main:users"),
                weight=20,
                icon="icons/users.html",
                check=lambda request: request.user.is_superuser,
            ),
            HumitifierMenuItem(
                "Access profiles",
                reverse("main:access_profiles"),
                weight=21,
                check=lambda request: request.user.is_superuser,
                icon="icons/shield.html",
            ),
        ],
    ),
)

Menu.add_item(
    "main",
    MenuItem(
        "Tasks",
        reverse("main:tasks"),
        weight=998,
        icon="icons/tasks.html",
        check=lambda request: request.user.is_superuser,
    ),
)


Menu.add_item(
    "main",
    MenuItem(
        "Django Admin",
        reverse("admin:index"),
        weight=999,
        icon="icons/admin.html",
        check=lambda request: request.user.is_superuser,
        separator=True,
        target="_blank",
    ),
)
