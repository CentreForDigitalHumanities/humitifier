from django.urls import reverse
from simple_menu import Menu, MenuItem

Menu.add_item(
    "main",
    MenuItem(
        "Dashboard",
        reverse("main:dashboard"),
        weight=1,
        icon="icons/dashboard.html",
    )
)

Menu.add_item(
    "main",
    MenuItem(
        "Users",
        reverse("main:users"),
        weight=20,
        icon="icons/users.html",
        separator=True,
    )
)

Menu.add_item(
    "main",
    MenuItem(
        "Access profiles",
        reverse("main:access_profiles"),
        weight=21,
        icon="icons/shield.html",
    )
)

Menu.add_item(
    "main",
    MenuItem(
        "OAuth2 Applications",
        reverse("main:oauth_applications"),
        weight=21,
        icon="icons/api.html",
    )
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
    )
)
