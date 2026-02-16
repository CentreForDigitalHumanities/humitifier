from django.urls import reverse
from simple_menu import Menu, MenuItem

from main.menu_item import HumitifierMenuItem

Menu.add_item(
    "main",
    HumitifierMenuItem(
        "Hosts",
        None,
        weight=10,
        separator=True,
        icon="icons/host.html",
        check=lambda request: request.user.is_authenticated,
        children=[
            HumitifierMenuItem(
                "List",
                reverse("hosts:list"),
                icon="icons/list.html",
                check=lambda request: request.user.is_authenticated,
            ),
            HumitifierMenuItem(
                lambda request: (
                    "Vibe Search" if request.user.wild_wasteland_mode else "Advanced Search"
                ),
                reverse("hosts:advanced_search"),
                icon="icons/search.html",
                check=lambda request: request.user.is_superuser,
            ),
            HumitifierMenuItem(
                "Data sources",
                reverse("hosts:data_sources"),
                icon="icons/databases.html",
                check=lambda request: request.user.is_authenticated
                and request.user.can_view_datasources,
            ),
            HumitifierMenuItem(
                "Scan specifications",
                reverse("scanning:scan_specs"),
                icon="icons/terminal.html",
                check=lambda request: request.user.is_superuser,
            ),
        ]
    ),
)
