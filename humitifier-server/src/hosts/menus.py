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
        "Data sources",
        reverse("hosts:data_sources"),
        weight=10,
        icon="icons/databases.html",
        check=lambda request: request.user.is_authenticated
        and request.user.can_view_datasources,
    ),
)
