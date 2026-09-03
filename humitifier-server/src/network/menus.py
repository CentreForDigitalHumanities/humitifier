from django.urls import reverse
from simple_menu import Menu
from main.menu_item import HumitifierMenuItem

Menu.add_item(
    "main",
    HumitifierMenuItem(
        "Networks",
        reverse("network:overview"),
        weight=15,
        icon="icons/globe.html",
        check=lambda request: request.user.is_authenticated,
    ),
)
