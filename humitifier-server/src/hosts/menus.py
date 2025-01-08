from django.urls import reverse
from simple_menu import Menu, MenuItem

Menu.add_item(
    "main",
    MenuItem(
        "Hosts",
        reverse("hosts:list"),
        weight=10,
        icon="icons/host.html",
        separator=True,
        check=lambda request: request.user.is_authenticated,
    ),
)

Menu.add_item(
    "main",
    MenuItem(
        "Tasks",
        reverse("hosts:tasks"),
        weight=10,
        icon="icons/tasks.html",
        check=lambda request: request.user.is_superuser,
    ),
)

Menu.add_item(
    "main",
    MenuItem(
        "Scan profiles",
        reverse("hosts:scan_profiles"),
        weight=10,
        icon="icons/terminal.html",
        check=lambda request: request.user.is_superuser,
    ),
)

Menu.add_item(
    "main",
    MenuItem(
        "Data sources",
        reverse("hosts:data_sources"),
        weight=10,
        icon="icons/databases.html",
        check=lambda request: request.user.is_authenticated
        and request.user.can_view_datasources,
    ),
)
