from django.urls import reverse
from simple_menu import Menu, MenuItem

from main.menu_item import HumitifierMenuItem

Menu.add_item(
    "main",
    HumitifierMenuItem(
        "API",
        None,
        weight=22,
        icon="icons/api.html",
        children=[
            HumitifierMenuItem(
                "Clients",
                reverse("api:oauth_applications"),
                check=lambda request: request.user.is_superuser,
                icon="icons/computer.html",
            ),
            HumitifierMenuItem(
                "Documentation",
                reverse("api:redoc"),
                icon="icons/document.html",
                target="_blank",
            ),
        ],
    ),
)
