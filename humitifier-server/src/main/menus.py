from django.urls import reverse
from simple_menu import Menu, MenuItem

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
    MenuItem(
        "Users",
        reverse("main:users"),
        weight=20,
        icon="icons/users.html",
        separator=True,
        check=lambda request: request.user.is_superuser,
    ),
)

Menu.add_item(
    "main",
    MenuItem(
        "Access profiles",
        reverse("main:access_profiles"),
        weight=21,
        check=lambda request: request.user.is_superuser,
        icon="icons/shield.html",
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
        target="_blank",
    ),
)


Menu.add_item(
    "main",
    MenuItem(
        "Tasks",
        reverse("main:tasks"),
        weight=998,
        icon="icons/tasks.html",
        separator=True,
        check=lambda request: request.user.is_superuser,
    ),
)
