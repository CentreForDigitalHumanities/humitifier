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
    )
)

Menu.add_item(
    "main",
    MenuItem(
        "Tasks",
        reverse("hosts:tasks"),
        weight=10,
        icon="icons/tasks.html",
    )
)

Menu.add_item(
    "main",
    MenuItem(
        "Scan profiles",
        reverse("hosts:scan_profiles"),
        weight=10,
        icon="icons/terminal.html",
    )
)

Menu.add_item(
    "main",
    MenuItem(
        "Data sources",
        reverse("hosts:data_sources"),
        weight=10,
        icon="icons/databases.html",
    )
)
